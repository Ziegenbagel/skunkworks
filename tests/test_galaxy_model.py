import unittest

from src.models.galaxy import (
    GalaxyMap,
    SectorCoordinates,
)
from src.intelligence.galaxy import GalaxyMapBuilder


class GalaxyModelTests(unittest.TestCase):
    def test_fcc_sector_has_twelve_neighbors(self):
        origin = SectorCoordinates(0, 0, 0)

        self.assertEqual(len(origin.neighbors()), 12)
        self.assertTrue(
            all(
                origin.distance_to(neighbor) == 1
                for neighbor in origin.neighbors()
            )
        )

    def test_invalid_fcc_coordinate_is_rejected(self):
        with self.assertRaises(ValueError):
            SectorCoordinates(1, 0, 0)

    def test_map_merges_visit_history(self):
        galaxy = GalaxyMap()
        record = galaxy.record_visit(
            {
                "relativeCoordinates": {
                    "x": 2,
                    "y": 0,
                    "z": 0,
                },
                "firstVisitedAt": "2026-01-01T00:00:00Z",
                "lastVisitedAt": "2026-01-02T00:00:00Z",
                "visitCount": 3,
            },
            probe_id=42,
        )

        self.assertEqual(record.visit_count, 3)
        self.assertEqual(
            record.observed_by_probe_ids,
            {42},
        )

    def test_builder_tracks_which_probes_visited(self):
        visit = {
            "relativeCoordinates": {
                "x": 2,
                "y": 0,
                "z": 0,
            },
            "visitCount": 1,
        }
        galaxy = GalaxyMapBuilder().build(
            {"visitedSectors": [visit]},
            {42: {"visitedSectors": [visit]}},
        )
        record = galaxy.get(
            SectorCoordinates(2, 0, 0)
        )

        self.assertEqual(
            record.observed_by_probe_ids,
            {42},
        )


if __name__ == "__main__":
    unittest.main()
