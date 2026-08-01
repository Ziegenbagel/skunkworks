import unittest

from src.api.capabilities import GameCapabilities


class RecordingClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, **kwargs):
        call = (method, path, kwargs)
        self.calls.append(call)
        return call


class ApiGatewayTests(unittest.TestCase):
    def setUp(self):
        self.client = RecordingClient()
        self.api = GameCapabilities(self.client)

    def test_probe_operations_are_explicitly_targeted(self):
        self.api.probes.move(
            42,
            {"x": 1, "y": 1, "z": 0},
        )

        self.assertEqual(
            self.client.calls[-1],
            (
                "POST",
                "/api/probe/42/move",
                {
                    "json": {
                        "target": {
                            "x": 1,
                            "y": 1,
                            "z": 0,
                        }
                    }
                },
            ),
        )

    def test_v105_movement_cancel_and_unread_filters_are_probe_scoped(self):
        self.api.probes.cancel_move(42)
        self.api.probes.alerts(42, status="unread")
        self.api.messaging.received(42, status="unread")

        self.assertEqual(self.client.calls[0], ("DELETE", "/api/probe/42/move", {}))
        self.assertEqual(self.client.calls[1], (
            "GET", "/api/probe/42/alerts", {"params": {"status": "unread"}},
        ))
        self.assertEqual(self.client.calls[2], (
            "GET", "/api/probe/42/messages", {"params": {"status": "unread"}},
        ))

    def test_manny_task_uses_target_probe(self):
        self.api.mannies.start_task(
            42,
            "mny_1",
            "mine",
            {"objectId": "asteroid-1"},
        )

        self.assertEqual(
            self.client.calls[-1][1],
            "/api/probe/42/mannies/mny_1/mine",
        )

    def test_messaging_uses_target_probe(self):
        self.api.messaging.send(
            42,
            {
                "recipient": {
                    "type": "probe",
                    "id": 7,
                },
                "body": "Status report",
            },
        )

        self.assertEqual(
            self.client.calls[-1][1],
            "/api/probe/42/messages",
        )

    def test_galaxy_observation_uses_relative_coordinates(self):
        self.api.galaxy.observe_sector(2, 0, 0)

        self.assertEqual(
            self.client.calls[-1],
            (
                "GET",
                "/api/sector",
                {"params": {"x": 2, "y": 0, "z": 0}},
            ),
        )

    def test_storage_and_logbook_are_probe_scoped(self):
        self.api.storage.containers(42)
        self.api.probes.logbook_pages(42)

        self.assertEqual(
            [call[1] for call in self.client.calls],
            [
                "/api/probe/42/storage-containers",
                "/api/probe/42/logbook-pages",
            ],
        )

    def test_manual_inventory_actions_use_documented_routes(self):
        self.api.storage.jettison(42, "stock-7", 0.25, "container-2")
        self.api.mannies.start_task(42, "mny_1", "detach-storage-container", {
            "containerId": "container-2", "mode": "drifting",
        })
        self.api.mannies.start_task(42, "mny_2", "transfer-deuterium-to-probe", {
            "targetProbeId": 7, "amount": 2.5,
        })

        self.assertEqual(self.client.calls[0], (
            "POST", "/api/probe/42/inventory/stock-7/jettison",
            {"json": {"amount": 0.25, "containerId": "container-2"}},
        ))
        self.assertEqual(self.client.calls[1][1], "/api/probe/42/mannies/mny_1/detach-storage-container")
        self.assertEqual(self.client.calls[2][1], "/api/probe/42/mannies/mny_2/transfer-deuterium-to-probe")


if __name__ == "__main__":
    unittest.main()
