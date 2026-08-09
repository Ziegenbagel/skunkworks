import unittest

from src.models.galaxy import (
    GalaxyMap,
    SectorCoordinates,
)
from src.safety.policy import TravelSafetyPolicy
from tests.test_planner_missions import build_operations


class TravelSafetyTests(unittest.TestCase):
    def test_game_collision_risk_table(self):
        safety = build_operations().travel_safety

        self.assertEqual(safety.collision_risk(2), 0)
        self.assertEqual(safety.collision_risk(3), 5)
        self.assertEqual(safety.collision_risk(4), 12)
        self.assertEqual(safety.collision_risk(5), 25)
        self.assertEqual(safety.collision_risk(6), 40)

    def test_container_risk_uses_dynamic_api_rule(self):
        operations = build_operations()
        operations.world.probe["inventory"]["containers"] = [
            {"kind": "probe"},
            *({"kind": "container"} for _ in range(7)),
        ]
        operations.world.hazard_context = {
            "damageWarnings": {
                "rule": {
                    "startsAtAdditionalContainers": 5,
                }
            }
        }

        self.assertEqual(
            operations.travel_safety.container_break_risk(),
            30,
        )

    def test_tanker_has_lower_fallback_threshold(self):
        operations = build_operations()
        operations.world.probe["model"] = "deuterium_tanker"

        self.assertEqual(
            operations.travel_safety.container_break_threshold(),
            2,
        )

    def test_cautious_route_segments_collision_risk(self):
        operations = build_operations()
        assessment = operations.travel_safety.assess(
            SectorCoordinates(3, 3, 0)
        )

        self.assertEqual(
            assessment.recommended.name,
            "segmented",
        )
        self.assertEqual(
            assessment.recommended.collision_risk_percent,
            0,
        )
        self.assertEqual(
            len(assessment.recommended.hops),
            3,
        )

    def test_scut_corridor_makes_direct_route_preferred(self):
        operations = build_operations()
        operations.world.hazard_context = {
            "scutNetworks": [
                {
                    "network": {
                        "relays": [
                            {
                                "status": "on",
                                "isTransitBeacon": True,
                                "sector": {
                                    "relative": {
                                        "x": 0,
                                        "y": 0,
                                        "z": 0,
                                    }
                                },
                            },
                            {
                                "status": "on",
                                "isTransitBeacon": True,
                                "sector": {
                                    "relative": {
                                        "x": 3,
                                        "y": 3,
                                        "z": 0,
                                    }
                                },
                            },
                        ]
                    }
                }
            ]
        }
        assessment = operations.travel_safety.assess(
            SectorCoordinates(3, 3, 0)
        )

        self.assertEqual(
            assessment.recommended.name,
            "direct",
        )
        self.assertTrue(
            assessment.recommended.scut_protected
        )

    def test_scut_route_requires_every_hop_to_remain_covered(self):
        operations = build_operations()
        operations.world.hazard_context = {
            "scutNetworks": [
                {
                    "network": {
                        "id": "home",
                        "relays": [
                            {
                                "status": "on",
                                "coverageRadiusSectors": 1,
                                "sector": {"relative": {"x": 0, "y": 0, "z": 0}},
                            }
                        ],
                    }
                }
            ]
        }

        self.assertTrue(operations.travel_safety.scut_route_covered(
            SectorCoordinates(0, 0, 0),
            (SectorCoordinates(1, 1, 0),),
        ))
        self.assertFalse(operations.travel_safety.scut_route_covered(
            SectorCoordinates(0, 0, 0),
            (SectorCoordinates(1, 1, 0), SectorCoordinates(2, 2, 0)),
        ))

    def test_known_black_hole_and_mannies_are_warned(self):
        operations = build_operations()
        destination = SectorCoordinates(1, 1, 0)
        galaxy = GalaxyMap()
        galaxy.record_observation(
            {
                "sector": {
                    "relativeCoordinates": {
                        "x": 1,
                        "y": 1,
                        "z": 0,
                    },
                    "objects": [
                        {"type": "black_hole"},
                    ],
                }
            }
        )
        operations.world.galaxy = galaxy
        operations.world.mannies["mannies"][0][
            "location"
        ] = {"type": "sector"}
        assessment = operations.travel_safety.assess(
            destination
        )
        codes = {
            hazard.code for hazard in assessment.hazards
        }

        self.assertIn("black_hole_entrapment", codes)
        self.assertIn("mannies_left_behind", codes)
        self.assertTrue(
            assessment.acknowledgement_recommended
        )

    def test_segmented_route_accounts_for_per_hop_fuel(self):
        operations = build_operations(fuel=5)
        assessment = operations.travel_safety.assess(
            SectorCoordinates(3, 3, 0)
        )

        self.assertEqual(
            assessment.recommended.name,
            "direct",
        )
        self.assertEqual(
            assessment.recommended.fuel_cost,
            2,
        )

    def test_unknown_hazards_cover_intermediate_sectors(self):
        assessment = build_operations().travel_safety.assess(
            SectorCoordinates(3, 3, 0)
        )

        self.assertEqual(
            len(assessment.unknown_hazard_sectors),
            3,
        )

    def test_profiles_change_acknowledgement_thresholds(self):
        cautious = TravelSafetyPolicy.from_dict(
            {"profile": "cautious"}
        )
        bold = TravelSafetyPolicy.from_dict(
            {"profile": "bold"}
        )

        self.assertEqual(
            cautious.collision_acknowledgement_percent,
            0,
        )
        self.assertEqual(
            bold.collision_acknowledgement_percent,
            25,
        )


if __name__ == "__main__":
    unittest.main()
