"""Translate actionable planner tasks into typed commands."""

import math
from dataclasses import replace

from .commands import Command, CommandType


class TaskCommandTranslator:
    def __init__(self, operations, probe_id, reserved_manny_ids=()):
        self.operations = operations
        self.probe_id = probe_id
        self._claimed_manny_ids = set()
        self._reserved_manny_ids = {str(item) for item in reserved_manny_ids}

    def translate(self, task):
        if task.constraints:
            return None

        handler = {
            "Launch Mission Missile": self._specialist,
            "Recover Salvage": self._specialist,
            "Transfer Salvage Manny": self._specialist,
            "Deliver Salvage Container": self._detach_transport_container,
            "Deploy SCUT Relay": self._infrastructure,
            "Activate SCUT Relay": self._infrastructure,
            "Install SCUT Beacon": self._infrastructure,
            "Load Hub Output": self._infrastructure,
            "Transfer Hub Manny": self._infrastructure,
            "Unload Hub Supply": self._infrastructure,
            "Clear Hub Container": self._infrastructure,
            "Return Hub Container": self._detach_transport_container,
            "Deliver Hub Container": self._detach_transport_container,
            "Install Probe Upgrade": self._upgrade,
            "Craft Item": self._craft,
            "Mine Resource": self._mine,
            "Mine Deuterium": self._mine,
            "Move Probe": self._move,
            "Cancel Automatic Travel": self._cancel_move,
            "Assemble Probe": self._assemble_probe,
            "Repair Probe": self._repair,
            "Inspect Sector Object": self._inspect_sector_object,
            "Recover Transport Container": self._recover_transport_container,
            "Detach Transport Container": self._detach_transport_container,
            "Deploy Miner Container": self._detach_transport_container,
            "Recover Miner Container": self._recover_transport_container,
            "Release Miner Container": self._detach_transport_container,
            "Transfer Deuterium": self._transfer_deuterium,
            "Refill Deuterium Tank": self._refill_deuterium_tank,
        }.get(task.action)

        command = handler(task) if handler is not None else None
        if command is not None and task.idempotency_scope:
            command = replace(command, metadata={
                **command.metadata,
                "idempotencyScope": task.idempotency_scope,
            })
        return command

    def _specialist(self, task):
        member = self._claim_idle_manny(required_id=task.target if task.action == "Transfer Salvage Manny" else None)
        if member is None:
            return None
        if task.action == "Launch Mission Missile":
            kind = CommandType.MANNY_LAUNCH_MISSILE
            payload = {"missileItemId":task.target, "targetId":task.metadata["targetId"]}
        elif task.action == "Transfer Salvage Manny":
            kind = CommandType.MANNY_TRANSFER_PROBE
            payload = {"targetProbeId":task.metadata["targetProbeId"]}
        else:
            kind = CommandType.MANNY_SALVAGE
            payload = {"objectId":task.target}
        return Command(kind, self.probe_id, payload, task.reason, task.priority,
            target_id=member["id"], source_action=task.action,
            metadata={**task.metadata, "workflowAuthorized":bool(task.workflow_authorized)})

    def _infrastructure(self, task):
        if task.action == "Transfer Hub Manny":
            member = self._claim_idle_manny(required_id=task.target)
            if member is None:
                return None
            return Command(CommandType.MANNY_TRANSFER_PROBE, self.probe_id,
                {"targetProbeId":int(task.metadata["targetProbeId"])}, task.reason, task.priority,
                target_id=member["id"], source_action=task.action,
                metadata={**task.metadata, "workflowAuthorized":bool(task.workflow_authorized)})
        if task.action == "Clear Hub Container":
            payload = dict(task.metadata["storageMove"])
            member = self._claim_idle_manny(excluded_ids=(payload.get("targetMannyId"),))
            if member is None:
                return None
            return Command(type=CommandType.MANNY_LOAD_HUB_OUTPUT, probe_id=self.probe_id,
                target_id=member["id"], payload=payload, reason=task.reason, priority=task.priority,
                source_action=task.action, metadata={**task.metadata, "workflowAuthorized":bool(task.workflow_authorized)})
        action = "Load Hub Output" if task.action == "Unload Hub Supply" else task.action
        kind, payload = {
            "Deploy SCUT Relay": (CommandType.DEPLOY_SCUT_RELAY, {"itemId": task.target}),
            "Activate SCUT Relay": (CommandType.MANNY_ACTIVATE_RELAY, {"relayId": task.target}),
            "Install SCUT Beacon": (CommandType.MANNY_INSTALL_BEACON, {"relayId": task.target}),
            "Load Hub Output": (CommandType.MANNY_LOAD_HUB_OUTPUT, {
                "kind": "item", "itemId": task.target, "toContainerId": task.metadata.get("toContainerId")}),
        }[action]
        member = None
        if kind != CommandType.DEPLOY_SCUT_RELAY:
            member = self._claim_idle_manny()
            if member is None:
                return None
        if "relayId" in payload:
            try:
                payload["relayId"] = int(payload["relayId"])
            except (TypeError, ValueError):
                return None
        return Command(type=kind, probe_id=self.probe_id, target_id=member["id"] if member else None,
                       payload=payload, reason=task.reason, priority=task.priority, source_action=task.action,
                       metadata={**task.metadata, "workflowAuthorized": bool(task.workflow_authorized)})

    def _recover_transport_container(self, task):
        manny = self._claim_idle_manny(
            allow_reserved=bool(task.metadata.get("minerCampaign")),
            required_id=task.metadata.get("assignedMannyId"),
            excluded_ids=task.metadata.get("excludedMannyIds", ()),
        )
        if manny is None or not task.target:
            return None
        return Command(
            type=CommandType.MANNY_RECOVER_STORAGE_CONTAINER,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload={
                "objectId": str(task.target),
                "source": str(task.metadata.get("source") or "drifting"),
            },
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                **task.metadata,
                "workflowAuthorized": bool(task.workflow_authorized),
                "mannyName": manny.get("name") or "Manny",
            },
        )

    def _detach_transport_container(self, task):
        manny = self._claim_idle_manny(
            allow_reserved=bool(task.metadata.get("minerCampaign")),
            required_id=task.metadata.get("assignedMannyId"),
            excluded_ids=task.metadata.get("excludedMannyIds", ()),
        )
        if manny is None or not task.target:
            return None
        return Command(
            type=CommandType.MANNY_DETACH_STORAGE_CONTAINER,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload={
                "containerId": str(task.target),
                "mode": str(task.metadata.get("mode") or "drifting"),
                **({"objectId": str(task.metadata["objectId"])}
                   if task.metadata.get("objectId") not in {None, ""} else {}),
            },
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                **task.metadata,
                "workflowAuthorized": bool(task.workflow_authorized),
                "mannyName": manny.get("name") or "Manny",
            },
        )

    def _inspect_sector_object(self, task):
        manny = self._claim_idle_manny()
        if manny is None or not task.target:
            return None
        return Command(
            type=CommandType.MANNY_INSPECT_SECTOR_OBJECT,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload={"objectId": task.target},
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                "workflowAuthorized": bool(task.workflow_authorized),
                "mannyName": manny.get("name") or "Manny",
                "objectName": task.metadata.get("objectName", task.target),
                "objectType": task.metadata.get("objectType", "sector_object"),
            },
        )

    def _cancel_move(self, task):
        return Command(
            type=CommandType.CANCEL_PROBE_MOVE,
            probe_id=self.probe_id,
            payload={},
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={"workflowAuthorized": bool(task.workflow_authorized)},
        )

    def _refill_deuterium_tank(self, task):
        manny = self._claim_idle_manny()
        if manny is None:
            return None
        return Command(
            type=CommandType.MANNY_REFILL_DEUTERIUM_TANK,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload={},
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                "workflowAuthorized": bool(task.workflow_authorized),
                "mannyName": manny.get("name") or "Manny",
            },
        )

    def _transfer_deuterium(self, task):
        manny = self._claim_idle_manny(
            allow_reserved=bool(task.metadata.get("minerCampaign")),
            required_id=task.metadata.get("assignedMannyId"),
            excluded_ids=task.metadata.get("excludedMannyIds", ()),
        )
        if manny is None:
            return None
        return Command(
            type=CommandType.MANNY_TRANSFER_DEUTERIUM,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload={
                "targetProbeId": int(task.target),
                "amount": round(float(task.quantity), 2),
            },
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                "resource": "deuterium",
                "transportTransfer": True,
                "minerCampaign": bool(task.metadata.get("minerCampaign")),
                "workflowAuthorized": bool(task.workflow_authorized),
                "mannyName": manny.get("name") or "Manny",
            },
        )

    def _repair(self, task):
        manny = self._claim_idle_manny()
        if manny is None:
            return None
        return Command(
            type=CommandType.MANNY_REPAIR,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload={"integrityPercent": round(float(task.quantity), 2)},
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={"mannyName": manny.get("name") or "Manny"},
        )

    def _upgrade(self, task):
        from src.operations.upgrades import installation_command
        from src.planner.desired_state import UpgradeGoal
        manny = self._claim_idle_manny()
        if manny is None:
            return None
        return installation_command(self.probe_id,
            UpgradeGoal(task.target, task.metadata["upgradeScope"], task.priority), manny["id"])

    def _craft(self, task):
        recipe = self.operations.manufacturing.recipes.get(
            task.target
        )

        if recipe is None:
            return None

        craftable_by = recipe.get("craftableBy", [])

        if "manny" in craftable_by:
            manny = self._claim_idle_manny()
            if manny is None:
                return None
            command_type = CommandType.MANNY_CRAFT
            target_id = manny["id"]
        elif "atomic_3d_printer" in craftable_by:
            command_type = CommandType.ATOMIC_PRINTER_CRAFT
            target_id = None
        else:
            return None

        # A recipe may legitimately be ordered repeatedly from the same Manny.
        # Scope idempotency to the inventory state that produced this proposal:
        # an unchanged refresh retains the same fingerprint, while completion of
        # the previous unit advances the state and permits the next order.
        stored_before = self.operations.manufacturing.inventory_count(
            task.target, include_active=False,
        )
        active_before = self.operations.manufacturing.active_production_count(
            task.target,
        )
        inventory_items = self.operations.world.probe.get("inventory", {}).get("items", ())
        output_item_ids = sorted(
            str(item.get("id", item.get("itemId", "")))
            for item in inventory_items
            if item.get("type") == task.target
        )

        return Command(
            type=command_type,
            probe_id=self.probe_id,
            target_id=target_id,
            payload={"recipe": task.target},
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                "remainingOrders": int(task.quantity),
                **task.metadata,
                "workflowAuthorized": bool(task.workflow_authorized),
                "storedBefore": int(stored_before),
                "activeBefore": int(active_before),
                # Counts can repeat after another recipe consumes an output.
                # Identities distinguish the legitimate replacement order from
                # the earlier successful command without weakening retries.
                "outputItemIds": output_item_ids,
                **({"mannyName": manny.get("name") or "Manny"}
                   if command_type == CommandType.MANNY_CRAFT else {}),
            },
        )

    def _mine(self, task):
        idle_count = len(self.operations.mining.idle_mannies())
        manny = self._claim_idle_manny(
            allow_reserved=bool(task.metadata.get("minerCampaign")),
            required_id=task.metadata.get("assignedMannyId"),
            excluded_ids=task.metadata.get("excludedMannyIds", ()),
        )
        resource_type = task.resource_type

        if manny is None or resource_type is None:
            return None

        cargo = manny.get("cargo") or {}
        trip_capacity = float(cargo.get("capacity", 0.05) or 0.05)
        uncovered = float(task.quantity)
        # The UI expresses deuterium delivery in tank ECE (5–55), while the
        # mining API retains the normalized 0.05–0.55 payload. Plan and reserve
        # in tank units, then normalize only the outbound targetAmount.
        unit_scale = 100.0 if resource_type == "deuterium" else 1.0
        per_order_maximum = min(
            float(task.maximum_order_amount) * unit_scale,
            55.0 if resource_type == "deuterium" else 0.55,
        )
        # Use only as many Mannys as the deficit requires at the configured
        # per-order maximum. The setting is a cap for each submitted order,
        # not a total to divide evenly between workers: full-size orders are
        # emitted first and only the final remainder may be smaller.
        planned_workers = max(1, min(
            idle_count,
            math.ceil(uncovered / per_order_maximum),
        ))
        target_amount = round(min(
            uncovered,
            per_order_maximum,
        ), 3)
        api_target_amount = round(target_amount / unit_scale, 4)
        trips = max(1, int((target_amount / (trip_capacity * unit_scale)) + 0.999999))
        target_container_id = task.metadata.get("targetContainerId")
        target_container = (
            {"id": target_container_id}
            if target_container_id not in {None, ""}
            else None if task.metadata.get("forceProbeStorage")
            else self._preferred_mining_container(task.target, resource_type)
        )
        sector = (
            (self.operations.world.probe.get("sector") or {}).get("relative") or {}
        )

        payload = {
            "objectId": task.target,
            "resources": [resource_type],
            "targetAmount": api_target_amount,
        }
        if target_container is not None:
            payload["targetContainerId"] = str(target_container["id"])

        return Command(
            type=CommandType.MANNY_MINE,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload=payload,
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                **task.metadata,
                "workflowAuthorized": bool(task.workflow_authorized),
                "requestedNeed": round(float(task.quantity), 3),
                "orderAmount": target_amount,
                "apiTargetAmount": api_target_amount,
                "mannyCargoPerTrip": trip_capacity,
                "apiUnitScale": unit_scale,
                "estimatedTrips": trips,
                "plannedMiningWorkers": planned_workers,
                "backgroundWork": bool(task.background_work),
                "remainingAmount": max(0, round(float(task.quantity) - target_amount, 3)),
                "mannyName": manny.get("name") or "Manny",
                "sector": {
                    axis: sector.get(axis) for axis in ("x", "y", "z")
                    if sector.get(axis) is not None
                },
            },
        )

    def _preferred_mining_container(self, asteroid_id, resource_type):
        """Prefer a resource-routed detached depot, then an unassigned empty one."""
        # Deuterium mining refills the probe's tank. A detached storage object
        # is not a valid destination for that API operation.
        if resource_type == "deuterium":
            return None
        candidates = []
        for container in self.operations.containers.detached():
            if self.operations.containers.free_capacity(container) <= 0:
                continue
            target = (
                container.get("targetObjectId")
                or container.get("asteroidId")
                or (container.get("location") or {}).get("objectId")
            )
            if target not in {None, "", asteroid_id}:
                continue
            rules = container.get("rules") or {}
            priority = tuple(rules.get("priority") or ())
            exclusions = set(rules.get("strictExclusion") or ()) | set(rules.get("exclusion") or ())
            if resource_type in exclusions:
                continue
            preference = 0 if resource_type in priority else 1 if not priority else 2
            candidates.append((
                preference,
                0 if target == asteroid_id else 1,
                -float(self.operations.containers.free_capacity(container)),
                str(container.get("id", "")),
                container,
            ))
        return min(candidates, default=(None, None, None, None, None))[-1]

    def _assemble_probe(self, task):
        from src.planner.assembly import empty_assembly_containers

        manny = self._claim_idle_manny()
        model = str(task.target or "").strip().lower().replace("-", "_")
        containers = empty_assembly_containers(self.operations)
        if manny is None or len(containers) < 2:
            return None
        payload = {"model": model, "containerIds": containers[:2]}
        return Command(
            type=CommandType.MANNY_ASSEMBLE_PROBE,
            probe_id=self.probe_id,
            target_id=manny["id"],
            payload=payload,
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata={
                "model": model, "durationSeconds": 10800,
                "mannyName": manny.get("name") or "Manny",
            },
        )

    def _move(self, task):
        route = task.route or self.operations.travel.route_to(
            task.destination
        )

        if not route:
            return None

        next_sector = route[0]
        metadata = {
            **dict(task.metadata or {}),
            "finalDestination": {
                "x": task.destination.x,
                "y": task.destination.y,
                "z": task.destination.z,
            },
            "remainingHops": len(route),
            "requireScutCoverage": task.require_scut_coverage,
            "routeRiskAcknowledged": task.risk_acknowledged,
            "workflowAuthorized": bool(task.workflow_authorized),
            "hazards": [
                {
                    "code": hazard.code,
                    "severity": hazard.severity,
                    "message": hazard.message,
                    "acknowledgementRecommended": (
                        hazard.acknowledgement_recommended
                    ),
                }
                for hazard in task.hazards
            ],
        }
        return Command(
            type=CommandType.MOVE_PROBE,
            probe_id=self.probe_id,
            payload={
                "target": {
                    "x": next_sector.x,
                    "y": next_sector.y,
                    "z": next_sector.z,
                }
            },
            reason=task.reason,
            priority=task.priority,
            source_action=task.action,
            metadata=metadata,
        )

    def _claim_idle_manny(self, *, allow_reserved=False, required_id=None, excluded_ids=()):
        excluded = {str(value) for value in excluded_ids}
        mannies = [item for item in self.operations.mining.idle_mannies()
                   if str(item["id"]) not in excluded
                   and (required_id is None or str(item["id"]) == str(required_id))]
        if allow_reserved:
            reserved = next((
                item for item in mannies
                if str(item["id"]) in self._reserved_manny_ids
                and item["id"] not in self._claimed_manny_ids
            ), None)
            if reserved is not None:
                self._claimed_manny_ids.add(reserved["id"])
                return reserved
        manny = next(
            (item for item in mannies
             if item["id"] not in self._claimed_manny_ids
             and (allow_reserved or str(item["id"]) not in self._reserved_manny_ids)),
            None,
        )
        if manny is not None:
            self._claimed_manny_ids.add(manny["id"])
        return manny

    def release_claim(self, command):
        """Release a planning-only Manny claim held by a blocked command."""

        if command is not None and command.target_id is not None:
            self._claimed_manny_ids.discard(command.target_id)
