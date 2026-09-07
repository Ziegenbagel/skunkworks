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
            not self._manny_is_aboard_current_probe(manny)
            for manny in relevant
        ):
            blockers.append("mannies_not_aboard")
        # API v128 exposes deployed autonomous units independently of the
        # ordinary Manny roster. A deployed Manny can be absent from, or lag
        # behind, that roster during an arrival/inspection transition. Treat
        # either a matching Manny ID or this probe as carrier as authoritative
        # evidence that automatic departure must wait.
        owned_ids = {str(manny.get("id")) for manny in mannies if manny.get("id") is not None}
        probe_id = str(self.world.probe.get("id"))
        for unit in (self.world.sector or {}).get("autonomousUnits", ()):
            kind = str(unit.get("kind", unit.get("type", ""))).casefold()
            if "manny" not in kind:
                continue
            carrier = unit.get("carrier") or {}
            belongs_to_probe = (
                str(unit.get("id")) in owned_ids
                or str(carrier.get("id")) == probe_id
                or str(unit.get("carrierProbeId", "")) == probe_id
            )
            spatial_state = str(unit.get("spatialState", "")).casefold()
            if belongs_to_probe and spatial_state not in {
                "aboard", "aboard_probe", "contained", "docked", "on_probe",
            }:
                blockers.append("mannies_not_aboard")
                break
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

    def _manny_is_aboard_current_probe(self, manny):
        location = manny.get("location") or {}
        location_type = str(location.get("type", "")).casefold().replace("-", "_")
        if location_type not in {"probe", "aboard_probe", "on_probe"}:
            return False
        carrier_id = (
            location.get("probeId")
            or (location.get("probe") or {}).get("id")
            or (location.get("carrier") or {}).get("id")
        )
        return carrier_id in {None, "", self.world.probe.get("id"), str(self.world.probe.get("id"))}
