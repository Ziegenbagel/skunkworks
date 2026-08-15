from src.ui.controller import MissionControlController, MissionControlDataService


class _Preferences:
    def __init__(self):
        self.values = {}

    def get_preference(self, key, default=None):
        return self.values.get(key, default)

    def set_preference(self, key, value):
        self.values[key] = value


class _NamingCapabilities:
    def __init__(self):
        self.renamed_mannies = []
        self.probes = type("Probes", (), {
            "list": lambda inner: {"probes": [
                {"id": 1, "name": "Hub One"},
                {"id": 2, "name": "Miner Two"},
            ]},
        })()
        self.mannies = type("Mannies", (), {
            "list": lambda inner, probe_id: {"mannies": [
                {"id": "m2", "name": "Old Two"},
                {"id": "m1", "name": "Old One"},
            ]},
            "rename": lambda inner, probe_id, manny_id, name: self.renamed_mannies.append(
                (probe_id, manny_id, name)
            ),
        })()


def test_fleet_prefix_inference_removes_default_role_and_ordinal():
    probes = [
        {"id": 2, "name": "Demo Explorer - 1", "isDefault": False},
        {"id": 1, "name": "Demo Skunkworks Hub", "isDefault": True},
    ]

    assert MissionControlDataService._infer_fleet_prefix(probes) == "Ziegenbagel Skunkworks"


def test_fleet_prefix_inference_preserves_meaningful_words():
    probes = [{"id": 1, "name": "Deep Space Works - 03", "isDefault": True}]

    assert MissionControlDataService._infer_fleet_prefix(probes) == "Deep Space Works"


def test_fleet_prefix_inference_handles_empty_probe_list():
    assert MissionControlDataService._infer_fleet_prefix([]) == ""


def test_manny_naming_policy_is_probe_scoped_and_never_renames_probe():
    preferences = _Preferences()
    service = MissionControlDataService(client=object(), data_engine=preferences)
    service.capabilities = _NamingCapabilities()

    result = service.save_probe_manny_naming_policy(
        2, {
            "enabled": True,
            "mannyTemplate": "{probe} Manny {number}",
            "numberDigits": 3,
        }, True,
    )

    assert result["probeId"] == 2
    assert result["renamedMannies"] == 2
    assert service.capabilities.renamed_mannies == [
        (2, "m1", "Miner Two Manny 001"),
        (2, "m2", "Miner Two Manny 002"),
    ]
    assert "probe_manny_naming_policy:2" in preferences.values
    assert "probe_manny_naming_policy:1" not in preferences.values


def test_legacy_number_token_migrates_its_visible_width():
    preferences = _Preferences()
    service = MissionControlDataService(client=object(), data_engine=preferences)
    service.capabilities = _NamingCapabilities()

    result = service.save_probe_manny_naming_policy(
        1, {"mannyTemplate": "Manny-{number:002d}"}, True,
    )

    assert result["policy"]["numberDigits"] == 3
    assert service.capabilities.renamed_mannies[0] == (1, "m1", "Manny-001")


def test_successful_naming_result_updates_visible_policy_before_refresh(monkeypatch):
    controller = MissionControlController.__new__(MissionControlController)
    controller._naming_worker = object()
    controller._dashboard = {"automation": {"namingPolicy": {"prefix": "OLD"}}}
    controller._focused_probe_id = 7
    changed = []
    refreshed = []
    monkeypatch.setattr(controller, "_set_error", lambda message: None)
    monkeypatch.setattr(controller, "_qt_safe", lambda value: value)
    monkeypatch.setattr(controller, "dashboardChanged", type("Signal", (), {"emit": lambda self: changed.append(True)})())
    monkeypatch.setattr(
        controller,
        "_start_refresh",
        lambda probe_id, prefer_cached_fleet=False: refreshed.append((probe_id, prefer_cached_fleet)),
    )

    controller._accept_fleet_naming({"policy": {"prefix": "Ziegenbagel Skunkworks"}})

    assert controller._dashboard["automation"]["namingPolicy"]["prefix"] == "Ziegenbagel Skunkworks"
    assert changed == [True]
    assert refreshed == [(7, True)]
