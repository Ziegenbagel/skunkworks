import unittest

from src.intelligence.resources import ResourceAnalyzer


class SectorNormalizationTests(unittest.TestCase):
    def test_blind_moving_sector_can_omit_objects(self):
        resources = ResourceAnalyzer().get_sector_resources(
            {
                "sector": {
                    "relativeCoordinates": {
                        "x": 0,
                        "y": 0,
                        "z": 0,
                    },
                    "knowledgeLevel": "detailed",
                    "confidence": 0,
                    "scan": {},
                },
            }
        )

        self.assertEqual(resources, [])


if __name__ == "__main__":
    unittest.main()
