"""Pure decisions for the Explorer fleet-role campaign."""

from dataclasses import dataclass
import re

from src.models.galaxy import SectorCoordinates
from src.planner.task import Task


@dataclass(frozen=True)
class ExplorerDecision:
    phase: str
    summary: str
    destination: SectorCoordinates | None = None
    tasks: tuple[Task, ...] = ()
    paused: bool = False


class ExplorerCampaignService:
    """Choose one safe next Explorer action without mutating game state."""

    INTERESTING_TYPES = frozenset({"dormant_construct", "others_mothership_wreck"})

    def __init__(self, operations):
        self.operations = operations

    def decide(self, *, mode="planetary_frontier", alerts=(), reserved=(), resource_need=None):
        current = self.operations.travel.current_sector()
        if current is None:
            return ExplorerDecision("waiting", "Current sector telemetry is unavailable.")
        contact = self._civilization_alert(alerts)
        if contact is not None:
            return ExplorerDecision(
                "contact_hold",
                "Habitable species contact requires operator approval before exploration continues. Review and acknowledge the contact alert in Safety to resume.",
                paused=True,
            )
        if resource_need:
            resource, target_amount = resource_need
            source = self._nearest_resource_source(current, resource)
            if source is None:
                return ExplorerDecision(
                    "resupply_wait",
                    f"{resource.replace('_', ' ').title()} is below its global floor, but no reachable known source exists inside SCUT.",
                    paused=True,
                )
            if source == current:
                return ExplorerDecision(
                    "resupplying",
                    f"Replenishing {resource.replace('_', ' ')} toward the global {target_amount:g} ECE floor before exploration resumes.",
                )
            return ExplorerDecision(
                "resupply_travel",
                f"Returning to the nearest known {resource.replace('_', ' ')} source inside SCUT before exploration resumes.",
                destination=source,
            )
        targets = self._interesting_objects()
        if targets:
            tasks = tuple(Task(
                action="Inspect Sector Object",
                target=str(item["id"]),
                reason=(
                    f"Explorer stopped to inspect {item['name']} with an actual idle Manny "
                    "before selecting another frontier sector."
                ),
                category="exploration",
                priority=1,
                workflow_authorized=True,
                metadata={"objectName": item["name"], "objectType": item["type"]},
            ) for item in targets)
            return ExplorerDecision(
                "inspecting", f"Inspecting {len(tasks)} discovery object(s) in this sector.",
                tasks=tasks,
            )
        candidates = self.frontier_candidates(current, reserved=reserved)
        if not candidates:
            return ExplorerDecision(
                "waiting", "No reachable unexplored sector is currently known inside SCUT coverage."
            )
        if mode == "planetary_frontier":
            planetary = [item for item in candidates if self._planet_evidence(item[1])]
            pool = planetary or candidates
            fallback = not planetary
        else:
            pool, fallback = candidates, False
        destination, _record, route = min(
            pool, key=lambda item: (len(item[2]), item[0].x, item[0].y, item[0].z)
        )
        qualifier = "planet-bearing frontier" if not fallback and mode == "planetary_frontier" else "nearest frontier"
        return ExplorerDecision(
            "travelling",
            f"Selected {qualifier} at {destination.x}:{destination.y}:{destination.z}; route remains inside SCUT.",
            destination=destination,
        )

    def frontier_candidates(self, current, *, reserved=()):
        reserved = set(reserved)
        records = self.operations.galaxy.known_sectors()
        visited = {item.coordinates for item in records if item.visit_count > 0}
        frontier = {neighbor for point in (visited or {current}) for neighbor in point.neighbors() if neighbor not in visited}
        # Include observed, unvisited sectors even when they are not adjacent to
        # the current probe; this is what lets an Explorer route toward the next
        # known frontier after all twelve local neighbors have been visited.
        frontier.update(item.coordinates for item in records if item.visit_count <= 0)
        result = []
        by_coordinate = {item.coordinates: item for item in records}
        for candidate in frontier:
            if candidate in reserved:
                continue
            route = self.operations.travel.route_to(candidate)
            if not route:
                continue
            if self.operations.travel_safety.scut_route_covered(current, route) is not True:
                continue
            result.append((candidate, by_coordinate.get(candidate), route))
        return result

    def _nearest_resource_source(self, current, resource):
        # The focused sector snapshot is newer and more complete than the
        # retained galaxy observation. If the normal mining service can select
        # this resource here, resupply in place rather than claiming no known
        # source or routing away from a visible deposit.
        mining = getattr(self.operations, "mining", None)
        if mining is not None and mining.best_target(resource) is not None:
            return current
        candidates = []
        for record in self.operations.galaxy.known_sectors():
            if not record.observed or not self._contains_resource(record.observed, resource):
                continue
            if record.coordinates == current:
                candidates.append((0, record.coordinates))
                continue
            route = self.operations.travel.route_to(record.coordinates)
            if route and self.operations.travel_safety.scut_route_covered(current, route) is True:
                candidates.append((len(route), record.coordinates))
        return min(candidates, default=(None, None), key=lambda item: item[0])[1]

    @classmethod
    def _contains_resource(cls, value, resource):
        if isinstance(value, dict):
            resources = value.get("resources") or {}
            if isinstance(resources, dict) and float(resources.get(resource, 0) or 0) > 0:
                return True
            return any(cls._contains_resource(item, resource) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(cls._contains_resource(item, resource) for item in value)
        return False

    def _interesting_objects(self):
        snapshot = (self.operations.world.sector.get("snapshot") or {}).get("sector", {})
        found = []
        def walk(values):
            for item in values or ():
                kind = re.sub(
                    r"([a-z0-9])([A-Z])", r"\1_\2", str(item.get("type", ""))
                ).lower().replace("-", "_").replace(" ", "_")
                observed_class = str(item.get("observedClass", "")).lower()
                state = " ".join(str(item.get(key, "")) for key in (
                    "status", "state", "condition", "summary", "name",
                )).lower()
                is_derelict_others = (
                    ("others" in kind or "others" in observed_class or "others" in state)
                    and any(token in state or token in kind for token in ("derelict", "wreck", "dormant"))
                )
                if (kind in self.INTERESTING_TYPES or is_derelict_others) and item.get("id") is not None:
                    if is_derelict_others and kind not in self.INTERESTING_TYPES:
                        kind = "others_mothership_wreck"
                    found.append({
                        "id": item["id"], "type": kind,
                        "name": item.get("name") or item.get("summary") or kind.replace("_", " ").title(),
                    })
                walk(item.get("objects"))
                walk(item.get("bookmarkTargets"))
        walk(snapshot.get("objects"))
        return tuple({str(item["id"]): item for item in found}.values())

    @staticmethod
    def _planet_evidence(record):
        if record is None or not record.observed:
            return False
        sector = (record.observed.get("sector") or record.observed)
        possible = " ".join(map(str, sector.get("possibleObjects", ()))).lower()
        estimates = sector.get("estimatedObjects", {}) or {}
        if "planet" in possible or int(estimates.get("planetCountMax", 0) or 0) > 0:
            return True
        def contains_planet(values):
            return any(
                "planet" in str(item.get("type", "")).lower()
                or contains_planet(item.get("objects", ()))
                or contains_planet(item.get("bookmarkTargets", ()))
                for item in values or ()
            )
        return contains_planet(sector.get("objects", ()))

    @staticmethod
    def _civilization_alert(alerts):
        for alert in alerts or ():
            if str(alert.get("status", "unread")).lower() in {"read", "acknowledged", "resolved"}:
                continue
            text = " ".join(str(alert.get(key, "")) for key in ("type", "code", "title", "summary", "message")).lower()
            if any(token in text for token in ("habitable species", "civilization", "intelligent life", "first contact")):
                return alert
        return None
