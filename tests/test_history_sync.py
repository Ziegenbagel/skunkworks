from src.application.history_sync import HistorySynchronizer


class RecordingEngine:
    def __init__(self):
        self.calls = []

    def record_records(self, domain, records, probe_id=None):
        self.calls.append((domain, list(records), probe_id))


class ProbeCapabilities:
    def alerts(self, probe_id):
        return [{"id": "alert-1", "summary": "Dormant construct discovered"}]

    def damage_warnings(self, probe_id):
        return {"damageWarnings": [{"id": "warning-1"}]}


class Capabilities:
    probes = ProbeCapabilities()


def test_lightweight_safety_sync_records_focused_probe_payload_variants():
    engine = RecordingEngine()

    failures = HistorySynchronizer(engine, Capabilities()).sync_safety(42)

    assert failures == {}
    assert engine.calls == [
        (
            "alerts",
            [{"id": "alert-1", "summary": "Dormant construct discovered"}],
            42,
        ),
        ("damage_warnings", [{"id": "warning-1"}], 42),
    ]
