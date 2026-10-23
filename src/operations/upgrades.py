"""Live requirements and protected stock for an explicitly selected upgrade."""

from math import isfinite

from src.execution.commands import Command, CommandType


def installation_command(probe_id, goal, manny_id=None):
    return Command(
        type=CommandType.MANNY_UPGRADE, probe_id=probe_id, target_id=manny_id,
        payload={"improvement": goal.improvement_id},
        reason="Install the selected probe upgrade.", priority=goal.priority,
        source_action="Install Probe Upgrade",
        metadata={"upgradeScope": goal.scope, "workflowAuthorized": True},
    )


class UpgradeService:
    def __init__(self, operations):
        self.operations = operations

    def assess(self, goal):
        result = {"active": goal is not None, "status": "", "summary": "",
                  "items": {}, "resources": {}, "ingredients": [],
                  "missingItems": {}, "missingResources": {}, "blockers": []}
        if goal is None:
            return result
        result.update(improvementId=goal.improvement_id, scope=goal.scope)
        world = self.operations.world
        improvement = next((row for row in
            (getattr(world, "hazard_context", {}) or {}).get("improvements", {}).get("improvements", ())
            if row.get("id") == goal.improvement_id), None)
        result["name"] = (improvement or {}).get("name") or goal.improvement_id.replace("_", " ").title()
        if improvement and improvement.get("done"):
            result.update(status="complete", summary="Upgrade installed.")
            return result
        engine = self.operations.data_engine
        accepted = engine is not None and engine.action_was_successful(
            installation_command(world.probe["id"], goal).fingerprint)
        active = any(self.operations.mannies._task_type(manny) == "improving_probe"
                     for manny in world.mannies.get("mannies", ()))
        if accepted:
            result.update(status="installing", summary=(
                "Installation accepted; waiting for the game's completion. "
                "If cancelled in game, cancel this goal and select it again."))
            return result
        if not improvement or not improvement.get("available") or not improvement.get("installableOnProbe", True):
            result.update(status="blocked", summary="Upgrade blueprint unavailable; waiting for live telemetry.",
                          blockers=["upgrade_unavailable"])
            return result
        if not isinstance(improvement.get("ingredients"), (list, tuple)):
            result.update(status="blocked", summary="Upgrade requirements unavailable.",
                          blockers=["upgrade_requirements_unavailable"])
            return result
        resources, items = self.operations.manufacturing.available_inputs()
        for ingredient in improvement["ingredients"]:
            kind, name = ingredient.get("kind"), ingredient.get("type")
            try:
                amount = float(ingredient.get("quantity", -1))
            except (ValueError, TypeError):
                amount = -1
            if kind not in {"item", "resource"} or not name or not isfinite(amount) or amount < 0 or (kind == "item" and not amount.is_integer()):
                result["blockers"].append("invalid_upgrade_requirements")
                continue
            target = result["items" if kind == "item" else "resources"]
            target[name] = target.get(name, 0) + amount
        for kind, required, available, missing in (
            ("item", result["items"], items, result["missingItems"]),
            ("resource", result["resources"], resources, result["missingResources"]),
        ):
            for name, amount in required.items():
                stored = available.get(name, 0)
                active_count = self.operations.manufacturing.active_production_count(name) if kind == "item" else 0
                short = max(0, amount - stored - active_count)
                if short:
                    missing[name] = short
                result["ingredients"].append({"type": name, "kind": kind, "required": amount,
                    "stored": stored, "active": active_count, "missing": short})
        result["status"] = "preparing"
        result["summary"] = "; ".join(
            f"{row['type'].replace('_', ' ')}: {row['stored']:g} stored, "
            f"{row['active']:g} active / {row['required']:g} required"
            for row in result["ingredients"]) or "No inputs required."
        if result["blockers"]:
            result["status"] = "blocked"
        elif all(row["stored"] >= row["required"] for row in result["ingredients"]):
            result["status"] = "ready"
        if active:
            # A manual or unidentified installation is not proof that this
            # campaign consumed its kit. Wait without releasing its stock.
            result.update(status="waiting", summary="An upgrade task is active; waiting for live completion.")
        return result

    def command_blockers(self, command, goal):
        """Protect the next upgrade's physical stock regardless of other priorities."""
        if goal is None:
            return ()
        if command.metadata.get("hubReceipt") and command.type in {CommandType.MANNY_LOAD_HUB_OUTPUT, CommandType.MANNY_DETACH_STORAGE_CONTAINER}:
            # Local unloading retains stock; receipt preflight permits only empty returns.
            return ()
        view = self.assess(goal)
        if view["status"] in {"complete", "installing"}:
            return ()
        own = command.metadata.get("upgradeScope") == goal.scope
        if command.type == CommandType.MANNY_UPGRADE:
            return () if own and view["status"] == "ready" else ("upgrade_not_ready",)
        if view["blockers"] and command.type in {
            CommandType.MANNY_CRAFT, CommandType.ATOMIC_PRINTER_CRAFT,
            CommandType.MANNY_ASSEMBLE_PROBE, CommandType.MANNY_REPAIR,
            CommandType.MANNY_LAUNCH_MISSILE, CommandType.MANNY_SALVAGE,
            CommandType.MANNY_TRANSFER_PROBE, CommandType.MANNY_TRANSFER_DEUTERIUM, CommandType.MANNY_DETACH_STORAGE_CONTAINER,
            CommandType.DEPLOY_SCUT_RELAY, CommandType.MANNY_ACTIVATE_RELAY,
            CommandType.MANNY_INSTALL_BEACON, CommandType.MANNY_LOAD_HUB_OUTPUT,
            CommandType.MOVE_PROBE,
        }:
            return ("upgrade_requirements_unavailable",)
        resources, items = self.operations.manufacturing.available_inputs()
        held_items = {key: min(value, items.get(key, 0)) for key, value in view["items"].items()}
        held_resources = {key: min(value, resources.get(key, 0)) for key, value in view["resources"].items()}
        needed_items, needed_resources = {}, {}
        if command.type in {CommandType.MANNY_CRAFT, CommandType.ATOMIC_PRINTER_CRAFT}:
            recipe = command.payload.get("recipe")
            plan = self.operations.manufacturing.production_plan(recipe, include_operational_constraints=False, use_inventory_items=True)
            if plan is None:
                return ("unknown_recipe",)
            needed_items = plan["consumed_inventory_items"]
            needed_resources = plan["required_resources"]
            if own:
                # Upgrade work can consume its own intermediates; later plans
                # rebuild any direct installation component spent by the game.
                held_items = {}
        elif command.type == CommandType.MANNY_ASSEMBLE_PROBE:
            from src.planner.assembly import PROBE_ASSEMBLY_REQUIREMENTS
            needed_items = dict(PROBE_ASSEMBLY_REQUIREMENTS.get(command.payload.get("model"), ()))
            needed_items["storage_container"] = needed_items.get("storage_container", 0) + 2
        elif command.type in {CommandType.DEPLOY_SCUT_RELAY, CommandType.MANNY_ACTIVATE_RELAY, CommandType.MANNY_INSTALL_BEACON}:
            item_type = {CommandType.DEPLOY_SCUT_RELAY: "scut_relay", CommandType.MANNY_ACTIVATE_RELAY: "integrated_circuit",
                         CommandType.MANNY_INSTALL_BEACON: "scut_transit_beacon"}[command.type]
            needed_items = {item_type: 1}
        elif command.type == CommandType.MANNY_LOAD_HUB_OUTPUT and not command.metadata.get("hubReceipt"):
            item = next((i for i in self.operations.world.probe.get("inventory", {}).get("items", [])
                         if str(i.get("id")) == str(command.payload.get("itemId"))), {})
            needed_items = {item.get("type"): 1}
        elif command.type == CommandType.MANNY_REPAIR:
            needed_resources = {"metals": float(command.payload.get("integrityPercent", 0)) * 0.01}
        elif command.type == CommandType.MOVE_PROBE:
            needed_resources = {"deuterium": self.operations.travel.fuel_cost() / 100}
        elif command.type == CommandType.MANNY_TRANSFER_DEUTERIUM:
            needed_resources = {"deuterium": float(command.payload.get("amount", 0)) / 100}
        elif command.type == CommandType.MANNY_DETACH_STORAGE_CONTAINER and not command.metadata.get("hubReceipt"):
            if any(held_items.values()) or any(held_resources.values()):
                return ("cargo_reserved_by_upgrade",)
        if any(items.get(key, 0) - held_items.get(key, 0) < amount
               for key, amount in needed_items.items() if held_items.get(key, 0)):
            return ("item_reserved_by_upgrade",)
        if any(resources.get(key, 0) - held_resources.get(key, 0) + 0.00001 < amount
               for key, amount in needed_resources.items() if held_resources.get(key, 0)):
            return ("resource_reserved_by_upgrade",)
        return ()
