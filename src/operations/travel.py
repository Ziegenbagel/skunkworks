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
        return (
            self.world.probe["telemetry_available"]
            and self.world.probe["status"] == "idle"
            and self.fuel_available() >= self.fuel_cost()
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

        return tuple(blockers)
