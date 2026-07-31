"""Explainable exploration routes and recovery search corridors."""

from dataclasses import dataclass

from .mission import OperationFactory


@dataclass(frozen=True)
class RouteScore:
    route: tuple
    score: float
    distance: int
    discovery_value: float
    fuel_opportunities: int
    scut_coverage: int
    hazard_count: int
    reasons: tuple[str, ...]


class ExplorationService:
    def __init__(self, operations):
        self.operations = operations

    def score_route(
        self, route, *, detour_budget=0, hazards=None,
        scut_sectors=(), fuel_sectors=(),
    ):
        hazards = hazards or {}
        route = tuple(route)
        shortest = max(1, len(route) - max(0, detour_budget))
        unvisited = sum(not self.operations.galaxy.visited(point) for point in route)
        fuel = sum(point in fuel_sectors for point in route)
        scut = sum(point in scut_sectors for point in route)
        hazard_count = sum(len(hazards.get(point, ())) for point in route)
        detour = max(0, len(route) - shortest)
        score = unvisited * 4 + fuel * 3 + scut * 2 - hazard_count * 8 - detour
        return RouteScore(
            route, score, len(route), unvisited, fuel, scut, hazard_count,
            (
                f"{unvisited} unvisited sectors",
                f"{fuel} fuel opportunities",
                f"{scut} SCUT-covered sectors",
                f"{hazard_count} known hazards",
            ),
        )

    def rank_routes(self, routes, **context):
        return tuple(
            sorted(
                (self.score_route(route, **context) for route in routes),
                key=lambda candidate: (-candidate.score, candidate.distance),
            )
        )

    def search_corridor(self, last_known, radius=1):
        """Breadth-first FCC corridor around a lost asset's last position."""
        seen = {last_known}
        frontier = [last_known]
        result = [last_known]
        for _ in range(max(0, radius)):
            next_frontier = []
            for sector in frontier:
                for neighbor in sector.neighbors():
                    if neighbor not in seen:
                        seen.add(neighbor)
                        next_frontier.append(neighbor)
                        result.append(neighbor)
            frontier = next_frontier
        return tuple(result)

    def interrupt(self, operation, event, *, requires_investigation=False):
        """Pause without losing mission intent and optionally create a side operation."""
        event_id = event.get("id", "unknown")
        paused = operation.pause(f"event:{event_id}")
        side_operation = None
        if requires_investigation:
            side_operation = OperationFactory.create(
                "investigation",
                probe_id=operation.probe_id,
                metadata={"interruptsOperationId": operation.id, "eventId": event_id},
            )
        return paused, side_operation

    @staticmethod
    def resume(operation):
        metadata = dict(operation.metadata)
        metadata.pop("pauseReason", None)
        from dataclasses import replace
        from .mission import OperationState
        return replace(operation, state=OperationState.ACTIVE, metadata=metadata)
