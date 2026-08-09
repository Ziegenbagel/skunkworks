"""History-ready galaxy and sector-map domain models."""

from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class SectorCoordinates:
    x: int
    y: int
    z: int

    def __post_init__(self):
        if (self.x + self.y + self.z) % 2 != 0:
            raise ValueError(
                "FCC sector coordinates require an even x+y+z."
            )

    @classmethod
    def from_api(cls, value):
        return cls(
            x=int(value["x"]),
            y=int(value["y"]),
            z=int(value["z"]),
        )

    def distance_to(self, other):
        differences = (
            abs(self.x - other.x),
            abs(self.y - other.y),
            abs(self.z - other.z),
        )
        # Each FCC edge changes exactly two coordinates by one. A route must
        # therefore satisfy both the largest single-axis displacement and
        # half of the total displacement. The parity constraint guarantees
        # the latter is integral.
        return max(max(differences), sum(differences) // 2)

    def neighbors(self):
        offsets = (
            (1, 1, 0),
            (1, -1, 0),
            (-1, 1, 0),
            (-1, -1, 0),
            (1, 0, 1),
            (1, 0, -1),
            (-1, 0, 1),
            (-1, 0, -1),
            (0, 1, 1),
            (0, 1, -1),
            (0, -1, 1),
            (0, -1, -1),
        )
        return tuple(
            SectorCoordinates(
                self.x + dx,
                self.y + dy,
                self.z + dz,
            )
            for dx, dy, dz in offsets
        )


@dataclass
class SectorRecord:
    coordinates: SectorCoordinates
    first_visited_at: str | None = None
    last_visited_at: str | None = None
    visit_count: int = 0
    observed: dict | None = None
    observed_by_probe_ids: set[int] = field(
        default_factory=set
    )


class GalaxyMap:
    """In-memory map designed for later persistence and visualization."""

    def __init__(self):
        self._sectors = {}

    def record_visit(self, visit, probe_id=None):
        coordinates = SectorCoordinates.from_api(
            visit["relativeCoordinates"]
        )
        record = self._sectors.setdefault(
            coordinates,
            SectorRecord(coordinates=coordinates),
        )
        record.first_visited_at = visit.get(
            "firstVisitedAt",
            record.first_visited_at,
        )
        record.last_visited_at = visit.get(
            "lastVisitedAt",
            record.last_visited_at,
        )
        record.visit_count = int(
            visit.get("visitCount", record.visit_count)
        )

        if probe_id is not None:
            record.observed_by_probe_ids.add(probe_id)

        return record

    def record_observation(self, observation, probe_id=None):
        relative = observation["sector"]["relativeCoordinates"]
        coordinates = SectorCoordinates.from_api(relative)
        record = self._sectors.setdefault(
            coordinates,
            SectorRecord(coordinates=coordinates),
        )
        record.observed = observation

        if probe_id is not None:
            record.observed_by_probe_ids.add(probe_id)

        return record

    def get(self, coordinates):
        return self._sectors.get(coordinates)

    def sectors(self):
        return tuple(self._sectors.values())
