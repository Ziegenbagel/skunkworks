"""Fleet roles, delivery cycles, and tanker rendezvous planning."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TankerDeliveryPlan:
    tanker_probe_id: int
    target_probe_id: int
    available_for_delivery: float
    requested_amount: float
    deliverable_amount: float
    target_free_capacity: float
    source_return_reserve: float
    transfer_minutes: int = 5
    blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class CargoDeliveryPlan:
    resource_type: str
    requested_amount: float
    source_available: float
    carrier_capacity: float
    target_free_capacity: float
    deliverable_amount: float
    remaining_amount: float
    trips_required: int
    blockers: tuple[str, ...] = ()


class FleetRoleService:
    VALID_ROLES = frozenset(
        {
            "hub",
            "miner",
            "transport",
            "deuterium_tanker",
            "explorer",
            "builder_support",
            "unassigned",
        }
    )

    def __init__(self, data_engine):
        self.data_engine = data_engine

    def assign(
        self,
        asset_type,
        asset_id,
        role,
        operation_id=None,
        metadata=None,
    ):
        if role not in self.VALID_ROLES:
            raise ValueError(f"Unknown fleet role: {role}")
        self.data_engine.assign_fleet_role(
            asset_type,
            asset_id,
            role,
            operation_id,
            metadata,
        )

    def all(self, asset_type=None):
        return self.data_engine.fleet_roles(asset_type)


class TankerLogisticsService:
    def plan_delivery(
        self,
        tanker,
        target,
        requested_amount,
        return_reserve,
    ):
        blockers = []
        if tanker.get("model") != "deuterium_tanker":
            blockers.append("source_not_tanker")
        if tanker.get("status") != "idle":
            blockers.append("tanker_unavailable")
        if target.get("status") != "idle":
            blockers.append("target_unavailable")
        if self._sector(tanker) != self._sector(target):
            blockers.append("rendezvous_required")

        source_fuel = tanker.get("fuel", {}).get("deuterium", 0)
        target_fuel = target.get("fuel", {}).get("deuterium", 0)
        target_max = target.get("fuel", {}).get("maxDeuterium", 0)
        available = max(0.0, source_fuel - return_reserve)
        target_free = max(0.0, target_max - target_fuel)
        deliverable = min(
            max(0.0, requested_amount),
            available,
            target_free,
        )
        if deliverable <= 0:
            blockers.append("no_transferable_deuterium")
        if deliverable >= source_fuel:
            blockers.append("source_reserve_required")

        return TankerDeliveryPlan(
            tanker_probe_id=tanker["id"],
            target_probe_id=target["id"],
            available_for_delivery=available,
            requested_amount=requested_amount,
            deliverable_amount=deliverable,
            target_free_capacity=target_free,
            source_return_reserve=return_reserve,
            blockers=tuple(dict.fromkeys(blockers)),
        )

    @staticmethod
    def _sector(probe):
        return (probe.get("sector") or {}).get("relative")


class CargoLogisticsService:
    def plan_delivery(
        self, resource_type, requested_amount, source_available,
        carrier_capacity, target_free_capacity,
    ):
        from math import ceil

        blockers = []
        if source_available <= 0:
            blockers.append("source_empty")
        if carrier_capacity <= 0:
            blockers.append("carrier_has_no_capacity")
        if target_free_capacity <= 0:
            blockers.append("target_storage_full")
        amount = min(
            max(0.0, requested_amount), max(0.0, source_available),
            max(0.0, carrier_capacity), max(0.0, target_free_capacity),
        )
        total_possible = min(
            max(0.0, requested_amount), max(0.0, source_available),
            max(0.0, target_free_capacity),
        )
        trips = (
            ceil(total_possible / carrier_capacity)
            if carrier_capacity > 0 and total_possible > 0 else 0
        )
        return CargoDeliveryPlan(
            resource_type, requested_amount, source_available,
            carrier_capacity, target_free_capacity, amount,
            max(0.0, requested_amount - amount), trips, tuple(blockers),
        )
