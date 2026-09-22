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

    def decide(
        self, *, mode="planetary_frontier", alerts=(), reserved=(),
        resource_need=None, completed_inspections=(),
    ):
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
            maximum_hops = None
            if resource == "deuterium":
                fuel = getattr(self.operations.world, "probe", {}).get("fuel") or {}
                available = float(fuel.get("deuterium", 0) or 0)
                fuel_cost = float(self.operations.travel.fuel_cost())
                maximum_hops = int((available + 0.00001) // fuel_cost) if fuel_cost > 0 else None
            source = self._nearest_resource_source(
                current, resource, maximum_hops=maximum_hops,
            )
            if source is None:
                if resource == "deuterium":
                    return ExplorerDecision(
                        "fuel_resupply_manual_hold",
                        "Fuel has reached its safety floor and no known Deuterium source is reachable with the remaining tank reserve. Automatic travel is paused; manual refueling operations are required.",
                        paused=True,
                    )
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
        active_inspections = self._active_inspection_targets()
        if active_inspections:
            return ExplorerDecision(
                "inspecting",
                "Waiting for the active Manny sector-object inspection to finish before exploration resumes.",
            )
        targets = self._interesting_objects(completed_inspections)
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
        destination, selected_record, route = min(
            pool, key=lambda item: (
                len(item[2]),
                # A scan is navigation intelligence, not exploration. When
                # equally close candidates exist, consume that intelligence
                # first while still requiring a physical fleet visit before
                # the sector leaves the frontier.
                0 if item[1] is not None and item[1].observed else 1,
                item[0].x, item[0].y, item[0].z,
            )
        )
        qualifier = "planet-bearing frontier" if not fallback and mode == "planetary_frontier" else "nearest frontier"
        scan_note = " It has been scanned but no owned probe has visited it." if selected_record is not None and selected_record.observed else ""
        return ExplorerDecision(
            "travelling",
            f"Selected {qualifier} at {destination.x}:{destination.y}:{destination.z}; route remains inside SCUT.{scan_note}",
            destination=destination,
        )

    def frontier_candidates(self, current, *, reserved=()):
        reserved = set(reserved)
        records = self.operations.galaxy.known_sectors()
        # Scans—even detailed, 100%-confidence scans—do not make a sector
        # explored. Only merged fleet visit history proves that an owned probe
        # physically reached it. Fleet-wide records and each probe's records
        # are already coalesced into this GalaxyMap.
        visited = {
            item.coordinates for item in records
            if self._physically_explored(item)
        }
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

    @staticmethod
    def _physically_explored(record):
        return int(record.visit_count or 0) > 0

    def _nearest_resource_source(self, current, resource, *, maximum_hops=None):
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
            if (route
                    and (maximum_hops is None or len(route) <= maximum_hops)
                    and self.operations.travel_safety.scut_route_covered(current, route) is True):
                candidates.append((len(route), record.coordinates))
        return min(candidates, default=(None, None), key=lambda item: item[0])[1]

    @classmethod
    def _contains_resource(cls, value, resource):
        if isinstance(value, dict):
            # Retained observations span several public API schemas. The
            # Galaxy Map already presents all of these as resource-bearing
            # sectors; campaign routing must consume the same evidence or it
            # can display a nearby Metals node while claiming no source exists.
            for key in (
                "resourceAmounts", "resources", "remainingResources",
            ):
                resources = value.get(key)
                if isinstance(resources, dict):
                    try:
                        if float(resources.get(resource, 0) or 0) > 0:
                            return True
                    except (TypeError, ValueError):
                        if resources.get(resource):
                            return True
                elif isinstance(resources, (list, tuple)):
                    for item in resources:
                        if not isinstance(item, dict):
                            continue
                        resource_type = (
                            item.get("type") or item.get("resourceType")
                            or item.get("name")
                        )
                        amount = item.get("amount", item.get("remaining", 1))
                        if resource_type == resource and amount not in (
                            0, 0.0, "0", None,
                        ):
                            return True
            resource_types = value.get("resourceTypes") or ()
            if resource in resource_types and "resourceAmounts" not in value:
                # Older scans sometimes report only a positive type hint. If
                # authoritative remaining amounts are present, the checks
                # above deliberately prevent a depleted target from routing.
                return True
            return any(cls._contains_resource(item, resource) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(cls._contains_resource(item, resource) for item in value)
        return False

    def _interesting_objects(self, completed_inspections=()):
        snapshot = (self.operations.world.sector.get("snapshot") or {}).get("sector", {})
        found = []
        unavailable = {str(item) for item in completed_inspections}

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
                if (
                    (kind in self.INTERESTING_TYPES or is_derelict_others)
                    and item.get("id") is not None
                    and str(item["id"]) not in unavailable
                ):
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

    def _active_inspection_targets(self):
        targets = set()
        mannies = getattr(self.operations.world, "mannies", {}) or {}
        for manny in mannies.get("mannies", ()):
            current = manny.get("currentTask")
            details = current if isinstance(current, dict) else manny.get("task") or {}
            task_type = current.get("type") if isinstance(current, dict) else current
            normalized = str(task_type or "").lower().replace("-", "_").replace(" ", "_")
            if normalized not in {
                "inspect_sector_object", "inspecting_sector_object",
                "sector_object_inspection",
            } or not isinstance(details, dict):
                continue
            payload = details.get("payload") if isinstance(details.get("payload"), dict) else {}
            target = (
                details.get("objectId") or details.get("targetObjectId")
                or details.get("targetId") or payload.get("objectId")
            )
            if target is not None:
                targets.add(str(target))
        return frozenset(targets)

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
