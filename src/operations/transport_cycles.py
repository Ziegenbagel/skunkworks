"""Durable, fuel-safe round-trip transport cycle planning."""

from dataclasses import dataclass
from enum import StrEnum

from src.models.galaxy import SectorCoordinates


class TransportCycleState(StrEnum):
    PLANNED = "planned"
    TO_SOURCE = "to_source"
    LOADING = "loading"
    TO_DESTINATION = "to_destination"
    UNLOADING = "unloading"
    TO_RETURN_POINT = "to_return_point"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass(frozen=True)
class RoundTripTransportPlan:
    probe_id: int
    resource_type: str
    source: SectorCoordinates
    destination: SectorCoordinates
    return_point: SectorCoordinates
    load_until_percent: float = 100
    unload_until_percent: float = 0
    fuel_per_hop: float = 1
    protected_deuterium: float = 0
    reserve_hops: int = 1
    refuel_sectors: tuple[SectorCoordinates, ...] = ()
    minimum_refuel_source_amount: float = 0
    repeat: bool = True

    def __post_init__(self):
        for name, value in (
            ("load_until_percent", self.load_until_percent),
            ("unload_until_percent", self.unload_until_percent),
        ):
            if not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100.")
        if self.unload_until_percent > self.load_until_percent:
            raise ValueError("Unload threshold cannot exceed load threshold.")
        if self.fuel_per_hop < 0 or self.protected_deuterium < 0:
            raise ValueError("Fuel costs and reserves cannot be negative.")
        if self.minimum_refuel_source_amount < 0:
            raise ValueError("Minimum refuel source amount cannot be negative.")

    @property
    def cycle_hops(self):
        return (
            self.source.distance_to(self.destination)
            + self.destination.distance_to(self.return_point)
            + self.return_point.distance_to(self.source)
        )

    @property
    def minimum_departure_deuterium(self):
        """Fuel protected for destination, return, contingency, and floor."""
        required_hops = self.cycle_hops + self.reserve_hops
        return self.protected_deuterium + required_hops * self.fuel_per_hop

    def transferable_deuterium(self, current_deuterium):
        """Tanker fuel available without consuming the protected return reserve."""
        return max(0.0, current_deuterium - self.minimum_departure_deuterium)

    def to_dict(self):
        coordinates = lambda value: {"x": value.x, "y": value.y, "z": value.z}
        return {
            "probeId": self.probe_id,
            "resourceType": self.resource_type,
            "source": coordinates(self.source),
            "destination": coordinates(self.destination),
            "returnPoint": coordinates(self.return_point),
            "loadUntilPercent": self.load_until_percent,
            "unloadUntilPercent": self.unload_until_percent,
            "fuelPerHop": self.fuel_per_hop,
            "protectedDeuterium": self.protected_deuterium,
            "reserveHops": self.reserve_hops,
            "refuelSectors": [coordinates(value) for value in self.refuel_sectors],
            "minimumRefuelSourceAmount": self.minimum_refuel_source_amount,
            "repeat": self.repeat,
        }


@dataclass(frozen=True)
class TransportCycleAssessment:
    state: TransportCycleState
    ready: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    required_deuterium: float
    transferable_deuterium: float
    cargo_percent: float


class RoundTripTransportService:
    def assess(
        self, plan, probe, *, cargo_amount, cargo_capacity, state,
        deuterium_sources=(), refill_manny_available=True,
    ):
        blockers = []
        warnings = []
        fuel = (probe.get("fuel") or {}).get("deuterium", 0)
        cargo_percent = cargo_amount / cargo_capacity * 100 if cargo_capacity else 0

        if probe.get("id") != plan.probe_id:
            blockers.append("wrong_transport_probe")
        if (
            plan.resource_type == "deuterium"
            and probe.get("model") != "deuterium_tanker"
        ):
            blockers.append("deuterium_requires_tanker")
        if probe.get("status") != "idle":
            blockers.append("probe_unavailable")
        if fuel < plan.minimum_departure_deuterium:
            blockers.append("return_deuterium_reserve_unmet")
        elif fuel <= plan.minimum_departure_deuterium * 1.1:
            warnings.append("deuterium_reserve_margin_low")

        blockers.extend(
            self._fuel_stop_blockers(
                plan, deuterium_sources, refill_manny_available
            )
        )

        if state == TransportCycleState.LOADING:
            ready = cargo_percent >= plan.load_until_percent
            if not ready:
                warnings.append("waiting_for_load_threshold")
        elif state == TransportCycleState.UNLOADING:
            ready = cargo_percent <= plan.unload_until_percent
            if not ready:
                warnings.append("waiting_for_unload_threshold")
        else:
            ready = True

        return TransportCycleAssessment(
            state=state,
            ready=ready and not blockers,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
            required_deuterium=plan.minimum_departure_deuterium,
            transferable_deuterium=plan.transferable_deuterium(fuel),
            cargo_percent=cargo_percent,
        )

    @staticmethod
    def _fuel_stop_blockers(plan, sources, refill_manny_available):
        if not plan.refuel_sectors:
            return ()
        blockers = []
        indexed = {}
        for source in sources:
            coordinates = source.get("coordinates")
            if isinstance(coordinates, dict):
                coordinates = SectorCoordinates.from_api(coordinates)
            indexed.setdefault(coordinates, []).append(source)
        for sector in plan.refuel_sectors:
            candidates = indexed.get(sector, ())
            fresh = tuple(source for source in candidates if source.get("fresh", False))
            if not candidates:
                blockers.append(f"deuterium_source_unknown:{sector.x},{sector.y},{sector.z}")
            elif not fresh:
                blockers.append(f"deuterium_source_stale:{sector.x},{sector.y},{sector.z}")
            elif max(source.get("amount", 0) for source in fresh) \
                    < plan.minimum_refuel_source_amount:
                blockers.append(f"deuterium_source_insufficient:{sector.x},{sector.y},{sector.z}")
        if not refill_manny_available:
            blockers.append("refill_manny_unavailable")
        return tuple(blockers)

    @staticmethod
    def next_state(plan, state):
        transitions = {
            TransportCycleState.PLANNED: TransportCycleState.TO_SOURCE,
            TransportCycleState.TO_SOURCE: TransportCycleState.LOADING,
            TransportCycleState.LOADING: TransportCycleState.TO_DESTINATION,
            TransportCycleState.TO_DESTINATION: TransportCycleState.UNLOADING,
            TransportCycleState.UNLOADING: TransportCycleState.TO_RETURN_POINT,
            TransportCycleState.TO_RETURN_POINT: (
                TransportCycleState.LOADING
                if plan.return_point == plan.source and plan.repeat
                else TransportCycleState.TO_SOURCE
                if plan.repeat
                else TransportCycleState.COMPLETED
            ),
        }
        return transitions.get(state, state)
