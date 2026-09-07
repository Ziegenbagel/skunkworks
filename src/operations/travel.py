from src.knowledge.movement import MovementKnowledge
from src.models.galaxy import SectorCoordinates


class TravelService:
    """Operational travel intelligence."""

    def __init__(self, world):
        self.world = world
        self.knowledge = MovementKnowledge()

    def fuel_available(self):
        return self.world.probe["fuel"].get(
            "deuterium",
            0,
        )

    def fuel_cost(self):
        return self.knowledge.fuel_cost()

    def fuel_percentage(self):
        fuel = self.world.probe["fuel"]
        maximum = fuel.get("maxDeuterium", 0)

        if maximum <= 0:
            return 0

        return fuel.get("deuterium", 0) / maximum * 100

    def travel_ready(self):
        integrity = float(
            (self.world.probe.get("systems") or {}).get("integrityPercent", 100)
            or 0
        )
        return (
            self.world.probe["telemetry_available"]
            and self.world.probe["status"] == "idle"
            and self.fuel_available() >= self.fuel_cost()
            and integrity >= 10
        )

    def current_sector(self):
        sector = self.world.probe.get("sector") or {}
        relative = sector.get("relative")
        return (
            SectorCoordinates.from_api(relative)
            if relative is not None
            else None
        )

    def route_to(self, target, maximum_hop_distance=1):
        """Return a shortest FCC route using one- or two-sector legs."""

        if maximum_hop_distance not in {1, 2}:
            raise ValueError("Maximum hop distance must be 1 or 2 sectors.")

        current = self.current_sector()

        if current is None:
            return None

        route = []

        while current != target:
            current_distance = current.distance_to(target)
            candidates = tuple(
                neighbor
                for neighbor in current.neighbors()
                if neighbor.distance_to(target) < current_distance
            )

            if not candidates:
                return None

            current = min(
                candidates,
                key=lambda neighbor: (
                    neighbor.distance_to(target),
                    neighbor.x,
                    neighbor.y,
                    neighbor.z,
                ),
            )
            route.append(current)

        if maximum_hop_distance == 1 or len(route) <= 1:
            return tuple(route)

        segmented = route[maximum_hop_distance - 1::maximum_hop_distance]
        if not segmented or segmented[-1] != target:
            segmented.append(target)
        return tuple(segmented)

    def travel_blockers(self, target):
        blockers = []
        current = self.current_sector()

        if current is None:
            blockers.append("current_sector_unknown")
        elif current == target:
            blockers.append("already_at_destination")

        if (
            current != target
            and self.world.probe["status"] != "idle"
        ):
            blockers.append("probe_unavailable")

        if (
            current != target
            and self.fuel_available() < self.fuel_cost()
        ):
            blockers.append("insufficient_fuel")

        integrity = float(
            (self.world.probe.get("systems") or {}).get("integrityPercent", 100)
            or 0
        )
        if current != target and integrity < 10:
            blockers.append("probe_integrity_too_low")

        return tuple(blockers)

    def active_movement_target(self):
        movement = self.world.probe.get("movement") or {}
        value = movement.get("target") or movement.get("destination")
        if not isinstance(value, dict):
            return None
        value = value.get("relative") or value.get("relativeCoordinates") or value
        try:
            return SectorCoordinates.from_api(value)
        except (KeyError, TypeError, ValueError):
            return None

    def automatic_manny_departure_blockers(self, target=None):
        """Block automatic departure unless off-probe Mannys are at the target."""

        mannies = tuple(self.world.mannies.get("mannies", ()))
        relevant = []
        for manny in mannies:
            location = manny.get("location") or {}
            relative = (location.get("sector") or {}).get("relative")
            at_recovery_target = False
            if location.get("type") != "probe" and target is not None and relative:
                try:
                    at_recovery_target = SectorCoordinates.from_api(relative) == target
                except (KeyError, TypeError, ValueError):
                    pass
            if not at_recovery_target:
                relevant.append(manny)
        blockers = []
        if any(manny.get("currentTask") is not None for manny in relevant):
            blockers.append("manny_tasks_in_progress")
        if any(
            (manny.get("location") or {}).get("type") != "probe"
            for manny in relevant
        ):
            blockers.append("mannies_not_aboard")
        # Accepted work may not yet have authoritative task telemetry. The
        # dispatch burst marks its Manny unavailable immediately; treat that
        # local claim as enough to invalidate a previously planned auto-jump.
        if any(
            manny.get("currentTask") is None
            and not manny.get("canReceiveOrders", False)
            for manny in relevant
        ):
            blockers.append("mannies_unavailable_for_travel")
        return tuple(blockers)
