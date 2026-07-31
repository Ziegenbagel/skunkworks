import unittest

from src.application.probe_selector import (
    ProbeSelectionError,
    ProbeSelector,
)


PROBE_DATA = {
    "defaultProbeId": 1,
    "probes": [
        {
            "id": 1,
            "name": "Alpha",
            "status": "idle",
            "isDefault": True,
            "isReachable": True,
        },
        {
            "id": 2,
            "name": "Beta",
            "status": "idle",
            "isDefault": False,
            "isReachable": True,
        },
    ],
}


class ProbeSelectorTests(unittest.TestCase):
    def test_noninteractive_mode_uses_default(self):
        selected = ProbeSelector(
            interactive=False
        ).select(PROBE_DATA, [])

        self.assertEqual(selected["id"], 1)

    def test_selects_by_id(self):
        selected = ProbeSelector().select(
            PROBE_DATA,
            ["--probe-id", "2"],
        )

        self.assertEqual(selected["name"], "Beta")

    def test_selects_by_case_insensitive_name(self):
        selected = ProbeSelector().select(
            PROBE_DATA,
            ["--probe-name", "beta"],
        )

        self.assertEqual(selected["id"], 2)

    def test_interactive_selector_uses_menu_position(self):
        output = []
        selected = ProbeSelector(
            input_fn=lambda _: "2",
            output_fn=output.append,
            interactive=True,
        ).select(PROBE_DATA, [])

        self.assertEqual(selected["id"], 2)
        self.assertTrue(
            any("Beta" in line for line in output)
        )

    def test_unknown_probe_fails_cleanly(self):
        with self.assertRaises(ProbeSelectionError):
            ProbeSelector().select(
                PROBE_DATA,
                ["--probe-id", "99"],
            )


if __name__ == "__main__":
    unittest.main()
