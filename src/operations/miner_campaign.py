"""Explainable, opt-in decisions for a stationary Miner-role probe."""

from dataclasses import dataclass

from src.planner.task import Task


@dataclass(frozen=True)
class MinerCampaignDecision:
    tasks: tuple[Task, ...] = ()
    phase: str = "paused"
    summary: str = "Miner automation is paused."
    paused: bool = True
    managed_resources: tuple[str, ...] = ()
    reserve_transfer_manny: bool = False


class MinerCampaignService:
    """Select bounded mining work with a full-tank Manny transfer reserve."""

    ORDINARY_RESOURCES = ("metals", "ice", "carbon_compounds")

    def __init__(self, operations):
        self.operations = operations

    def decide(self, settings, *, target_probe=None, maximum_mining_order_amount=0.55):
        if not settings.get("miningEnabled", False):
            return MinerCampaignDecision()
        mode = str(settings.get("resourceMode") or "deuterium")
        selected = []
        if mode in {"deuterium", "all"}:
            selected.append("deuterium")
        if mode in {"resources", "all"}:
            enabled = settings.get("ordinaryResources", ())
            selected.extend(item for item in self.ORDINARY_RESOURCES if item in enabled)
        managed = tuple(dict.fromkeys(selected))
        idle = self.operations.mining.idle_mannies()
        ordinary_worker_limit = max(
            1, min(4, int(settings.get("maximumMiningMannies", 4) or 4))
        )
        fuel = self.operations.world.probe.get("fuel") or {}
        fuel_amount = float(fuel.get("deuterium", 0) or 0)
        fuel_maximum = float(fuel.get("maxDeuterium", 0) or 0)
        deuterium_full = (
            "deuterium" in managed and fuel_maximum > 0
            and fuel_amount + 0.00001 >= fuel_maximum
        )
        tasks = []
        if "deuterium" in managed:
            transfer = self._deuterium_transfer(settings, target_probe)
            if transfer is not None:
                tasks.append(transfer)
        active = self.operations.mining.active_commitments()
        for resource in managed:
            if resource == "deuterium":
                # Every idle Manny mines until the tank is full. Once full,
                # retain exactly one aboard for transfer and let the rest mine
                # into their own waiting cargo state.
                remaining_workers = max(0, len(idle) - (1 if deuterium_full else 0))
            else:
                remaining_workers = min(ordinary_worker_limit, len(idle) - len(tasks))
            if remaining_workers <= 0:
                continue
            target = self.operations.mining.best_target(resource)
            if target is None:
                continue
            need = self._mineable_need(
                resource, target, active, allow_waiting=deuterium_full,
            )
            while need > 0.00001 and remaining_workers > 0:
                order_limit = (
                    float(maximum_mining_order_amount) * 100.0
                    if resource == "deuterium" else 0.25
                )
                order = min(need, order_limit)
                tasks.append(Task(
                    action="Mine Resource", category="mining",
                    # Retain the changing uncovered campaign amount in command
                    # identity. A later completed trip may legitimately send
                    # the same Manny back to the same asteroid.
                    target=str(target["id"]), quantity=round(need, 3),
                    maximum_order_amount=(
                        float(maximum_mining_order_amount)
                        if resource == "deuterium" else 0.25
                    ), resource_type=resource,
                    priority=1, workflow_authorized=True,
                    idempotency_scope=f"miner:{resource}:{target['id']}",
                    reason=(
                        f"Miner campaign is extracting {resource.replace('_', ' ')}."
                        + (" The full tank reserves one Manny for transfer; this worker may wait with mined fuel until capacity opens."
                           if resource == "deuterium" and deuterium_full else "")
                    ),
                    metadata={"minerCampaign": True},
                ))
                need -= order
                remaining_workers -= 1
        if tasks:
            transferring = any(task.action == "Transfer Deuterium" for task in tasks)
            return MinerCampaignDecision(
                tasks=tuple(tasks),
                phase="transferring_deuterium" if transferring and len(tasks) == 1 else "mining",
                paused=False,
                summary=("Tank is full; prepared transfer to the selected receiver."
                         if transferring and len(tasks) == 1 else
                         f"Prepared {len(tasks)} Miner campaign order(s)."
                         + (" One Manny is reserved for the full-tank transfer."
                            if deuterium_full else "")),
                managed_resources=managed,
                reserve_transfer_manny=deuterium_full,
            )
        deuterium_wait = self._deuterium_wait_status(settings, target_probe)
        if "deuterium" in managed and deuterium_wait is not None:
            phase, summary = deuterium_wait
            return MinerCampaignDecision(
                phase=phase, paused=False, summary=summary,
                managed_resources=managed,
                reserve_transfer_manny=deuterium_full,
            )
        return MinerCampaignDecision(
            phase="waiting_for_resource", paused=False,
            summary="No selected resource is currently mineable in this sector.",
            managed_resources=managed,
        )

    def _deuterium_wait_status(self, settings, target_probe):
        fuel = self.operations.world.probe.get("fuel") or {}
        amount = float(fuel.get("deuterium", 0) or 0)
        maximum = float(fuel.get("maxDeuterium", 0) or 0)
        if maximum <= 0 or amount + 0.00001 < maximum:
            return None
        target_id = settings.get("deuteriumTransportProbeId")
        if target_id in {None, "", -1, "-1"} or target_probe is None:
            return ("tank_full_awaiting_receiver",
                    f"Deuterium tank is full at {amount:g}/{maximum:g} ECE. Select an available receiver.")
        if self._sector(self.operations.world.probe) != self._sector(target_probe):
            return ("tank_full_awaiting_rendezvous",
                    f"Deuterium tank is full at {amount:g}/{maximum:g} ECE. Waiting for the selected receiver to rendezvous in this sector.")
        target_fuel = target_probe.get("fuel") or {}
        target_amount = float(target_fuel.get("deuterium", 0) or 0)
        target_maximum = float(target_fuel.get("maxDeuterium", 0) or 0)
        if target_maximum <= target_amount + 0.00001:
            return ("tank_full_receiver_full",
                    f"Deuterium tank is full at {amount:g}/{maximum:g} ECE, but the selected receiver has no free fuel capacity.")
        return None

    def _deuterium_transfer(self, settings, target_probe):
        target_id = settings.get("deuteriumTransportProbeId")
        if target_id in {None, "", -1, "-1"} or target_probe is None:
            return None
        source = self.operations.world.probe
        source_fuel = source.get("fuel") or {}
        amount = float(source_fuel.get("deuterium", 0) or 0)
        maximum = float(source_fuel.get("maxDeuterium", 0) or 0)
        if maximum <= 0 or amount + 0.00001 < maximum:
            return None
        if self._sector(source) != self._sector(target_probe):
            return None
        target_fuel = target_probe.get("fuel") or {}
        target_free = max(0.0, float(target_fuel.get("maxDeuterium", 0) or 0)
                          - float(target_fuel.get("deuterium", 0) or 0))
        deliverable = min(max(0.0, amount - 1.0), target_free)
        if deliverable <= 0.00001:
            return None
        return Task(
            action="Transfer Deuterium", category="miner_logistics",
            target=str(target_id), quantity=round(deliverable, 2), priority=1,
            workflow_authorized=True,
            idempotency_scope=f"miner-transfer:{target_id}:{amount:g}",
            reason=("Miner tank is full; transfer mined Deuterium to the selected "
                    "same-sector Transport probe before resuming extraction."),
            metadata={"minerCampaign": True},
        )

    @staticmethod
    def _sector(probe):
        sector = probe.get("sector") or {}
        return sector.get("relative") or sector.get("relativeCoordinates")

    def _mineable_need(self, resource, target, active, *, allow_waiting=False):
        available = max(0.0, float(target.get("available_amount", 0) or 0))
        committed = max(0.0, float(active.get(resource, 0) or 0))
        if resource == "deuterium":
            if allow_waiting:
                return max(0.0, available - committed)
            fuel = self.operations.world.probe.get("fuel") or {}
            free = max(0.0, float(fuel.get("maxDeuterium", 0) or 0)
                       - float(fuel.get("deuterium", 0) or 0))
        else:
            free = max(0.0, float(self.operations.inventory.mining_return_capacity(active)))
        return max(0.0, min(available, free) - committed)
