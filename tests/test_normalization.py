import unittest
from types import SimpleNamespace

from src.intelligence.probe import ProbeAnalyzer
from src.operations.probes import ProbeService
from src.operations.travel import TravelService


class NormalizationTests(unittest.TestCase):
    def test_probe_preserves_top_level_transit_telemetry(self):
        probe = ProbeAnalyzer().analyze({
            "id": 7, "name": "Traveler", "model": "generic", "status": "cruising",
            "velocityC": 0.24,
            "heading": {"x": 0.7071, "y": -0.7071, "z": 0},
            "movement": {"phase": "cruising"},
        })

        self.assertEqual(probe["movement"]["velocity"], 0.24)
        self.assertEqual(probe["movement"]["heading"]["x"], 0.7071)

    def test_limited_probe_telemetry_is_safe(self):
        probe = ProbeAnalyzer().analyze(
            {
                "id": 2,
                "name": "Remote",
                "status": "out_of_scut_range",
                "sector": {
                    "relative": {"x": 2, "y": 0, "z": 0}
                },
            }
        )

        self.assertFalse(probe["telemetry_available"])
        self.assertEqual(probe["inventory"]["items"], [])

    def test_current_probe_model_is_preserved(self):
        probe = ProbeAnalyzer().analyze(
            {
                "id": 2,
                "name": "Tanker",
                "model": "deuterium_tanker",
                "status": "idle",
                "sensorMode": "normal",
                "fuel": {
                    "deuterium": 400,
                    "maxDeuterium": 400,
                },
            }
        )

        self.assertEqual(
            probe["model"],
            "deuterium_tanker",
        )

    def test_cruising_probe_is_traveling(self):
        world = SimpleNamespace(
            probe={"status": "cruising"}
        )

        self.assertTrue(
            ProbeService(world).is_traveling()
        )

    def test_travel_requires_fixed_fuel_cost(self):
        world = SimpleNamespace(
            probe={
                "status": "idle",
                "telemetry_available": True,
                "fuel": {
                    "deuterium": 1.99,
                    "maxDeuterium": 100,
                },
            }
        )
        travel = TravelService(world)

        self.assertEqual(travel.fuel_cost(), 2.0)
        self.assertFalse(travel.travel_ready())


if __name__ == "__main__":
    unittest.main()
