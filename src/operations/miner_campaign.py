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


class MinerCampaignService:
    """Select bounded mining work while retaining one Manny for logistics."""

    ORDINARY_RESOURCES = ("metals", "ice", "carbon_compounds")

    def __init__(self, operations):
        self.operations = operations

    def decide(self, settings, *, target_probe=None):
        if not settings.get("miningEnabled", False):
            return MinerCampaignDecision()
        mode = str(settings.get("resourceMode") or "deuterium")
        selected = []
        if mode in {"deuterium", "all"}:
            selected.append("deuterium")
        if mode in {"resources", "all"}:
            enabled = settings.get("ordinaryResources") or self.ORDINARY_RESOURCES
            selected.extend(item for item in self.ORDINARY_RESOURCES if item in enabled)
        managed = tuple(dict.fromkeys(selected))
        idle = self.operations.mining.idle_mannies()
        worker_limit = max(1, min(4, int(settings.get("maximumMiningMannies", 4) or 4)))
        available_workers = min(worker_limit, max(0, len(idle) - 1))
        if available_workers <= 0:
            return MinerCampaignDecision(
                phase="logistics_reserve", paused=False,
                summary="Waiting for another idle Manny; one Manny remains reserved for logistics.",
                managed_resources=managed,
            )
        tasks = []
        if "deuterium" in managed:
            transfer = self._deuterium_transfer(settings, target_probe)
            if transfer is not None:
                tasks.append(transfer)
        active = self.operations.mining.active_commitments()
        remaining_workers = max(0, available_workers - len(tasks))
        for resource in managed:
            if remaining_workers <= 0:
                break
            target = self.operations.mining.best_target(resource)
            if target is None:
                continue
            need = self._mineable_need(resource, target, active)
            while need > 0.00001 and remaining_workers > 0:
                order = min(need, 55.0 if resource == "deuterium" else 0.55)
                tasks.append(Task(
                    action="Mine Resource", category="mining",
                    # Retain the changing uncovered campaign amount in command
                    # identity. A later completed trip may legitimately send
                    # the same Manny back to the same asteroid.
                    target=str(target["id"]), quantity=round(need, 3),
                    maximum_order_amount=0.55, resource_type=resource,
                    priority=1, workflow_authorized=True,
                    idempotency_scope=f"miner:{resource}:{target['id']}",
                    reason=(f"Miner campaign is extracting {resource.replace('_', ' ')} "
                            "while retaining one idle Manny aboard for logistics."),
                    metadata={"minerCampaign": True},
                ))
                need -= order
                remaining_workers -= 1
        if tasks:
            return MinerCampaignDecision(
                tasks=tuple(tasks), phase="mining", paused=False,
                summary=(f"Prepared {len(tasks)} mining order(s); one idle Manny is reserved "
                         "for transfer and container logistics."),
                managed_resources=managed,
            )
        return MinerCampaignDecision(
            phase="waiting_for_resource", paused=False,
            summary="No selected resource is currently mineable in this sector.",
            managed_resources=managed,
        )

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
            action="Transfer Deuterium", category="operations",
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

    def _mineable_need(self, resource, target, active):
        available = max(0.0, float(target.get("available_amount", 0) or 0))
        committed = max(0.0, float(active.get(resource, 0) or 0))
        if resource == "deuterium":
            fuel = self.operations.world.probe.get("fuel") or {}
            free = max(0.0, float(fuel.get("maxDeuterium", 0) or 0)
                       - float(fuel.get("deuterium", 0) or 0))
        else:
            free = max(0.0, float(self.operations.inventory.mining_return_capacity(active)))
        return max(0.0, min(available, free) - committed)
