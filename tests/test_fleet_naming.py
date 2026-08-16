import requests

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
        self.manny_rows = [
            {"id": "m2", "name": "Old Two"},
            {"id": "m1", "name": "Old One"},
        ]
        self.probes = type("Probes", (), {
            "list": lambda inner: {"probes": [
                {"id": 1, "name": "Hub One"},
                {"id": 2, "name": "Miner Two"},
            ]},
        })()
        self.mannies = type("Mannies", (), {
            "list": lambda inner, probe_id: {"mannies": self.manny_rows},
            "rename": lambda inner, probe_id, manny_id, name: self.renamed_mannies.append(
                (probe_id, manny_id, name)
            ),
        })()


class _ConflictNamingCapabilities(_NamingCapabilities):
    def __init__(self):
        super().__init__()
        self.manny_rows = [
            {"id": "m1", "name": "Hub - B"},
            {"id": "m2", "name": "Hub - A"},
        ]

        def rename(inner, probe_id, manny_id, name):
            if any(
                item["id"] != manny_id and item["name"] == name
                for item in self.manny_rows
            ):
                response = type("Response", (), {"status_code": 409})()
                raise requests.HTTPError("conflict", response=response)
            item = next(row for row in self.manny_rows if row["id"] == manny_id)
            item["name"] = name
            self.renamed_mannies.append((probe_id, manny_id, name))

        self.mannies.rename = rename.__get__(self.mannies, type(self.mannies))


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


def test_naming_uses_accepted_focus_when_fleet_index_omits_probe():
    preferences = _Preferences()
    service = MissionControlDataService(client=object(), data_engine=preferences)
    service.capabilities = _NamingCapabilities()
    service.capabilities.probes = type("IncompleteProbes", (), {
        "list": lambda inner: {"probes": [{"id": 1, "name": "Hub One"}]},
    })()

    result = service.save_probe_manny_naming_policy(
        2,
        {"mannyTemplate": "Tanker - {number}", "sequenceStyle": "letters"},
        True,
        probe_name="Fuel Tanker",
    )

    assert result["probeId"] == 2
    assert "probe_manny_naming_policy:2" in preferences.values
    assert service.capabilities.renamed_mannies[0] == (2, "m1", "Tanker - A")


def test_legacy_number_token_migrates_its_visible_width():
    preferences = _Preferences()
    service = MissionControlDataService(client=object(), data_engine=preferences)
    service.capabilities = _NamingCapabilities()

    result = service.save_probe_manny_naming_policy(
        1, {"mannyTemplate": "Manny-{number:002d}"}, True,
    )

    assert result["policy"]["numberDigits"] == 3
    assert service.capabilities.renamed_mannies[0] == (1, "m1", "Manny-001")


def test_letter_sequence_rolls_from_z_to_aa():
    values = [
        MissionControlDataService._letter_sequence(number)
        for number in (1, 26, 27, 28, 52, 53)
    ]

    assert values == ["A", "Z", "Aa", "Ab", "Az", "Ba"]


def test_new_manny_appends_to_sequence_even_when_its_id_sorts_first():
    preferences = _Preferences()
    service = MissionControlDataService(client=object(), data_engine=preferences)
    service.capabilities = _NamingCapabilities()
    policy = {
        "enabled": True,
        "mannyTemplate": "DemoHub - {number}",
        "sequenceStyle": "letters",
    }
    service.save_probe_manny_naming_policy(1, policy, True)
    service.capabilities.renamed_mannies.clear()
    service.capabilities.manny_rows.append({"id": "a0", "name": "manny-1"})

    result = service.save_probe_manny_naming_policy(1, policy, False)

    assert result["renamedMannies"] == 1
    assert service.capabilities.renamed_mannies == [(1, "a0", "DemoHub - C")]


def test_refresh_detects_unseen_manny_without_waiting_for_periodic_audit():
    controller = MissionControlController.__new__(MissionControlController)
    controller._focused_probe_id = 1
    controller.settings_engine = _Preferences()
    controller.settings_engine.set_preference(
        "probe_manny_naming_seen:1", '["m1", "m2"]',
    )

    unseen = controller._unseen_manny_ids({
        "focusedProbeId": 1,
        "inventoryManagement": {
            "mannies": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}],
        },
    })

    assert unseen == ("m3",)


def test_refresh_uses_nested_focus_id_during_startup():
    controller = MissionControlController.__new__(MissionControlController)
    controller._focused_probe_id = -1
    controller.settings_engine = _Preferences()
    controller.settings_engine.set_preference(
        "probe_manny_naming_seen:644", '["m1"]',
    )

    unseen = controller._unseen_manny_ids({
        "focus": {"probeId": 644, "name": "Hub"},
        "inventoryManagement": {"mannies": [{"id": "m1"}, {"id": "m2"}]},
    })

    assert unseen == ("m2",)


def test_invalid_probe_id_is_rejected_before_any_api_request():
    service = MissionControlDataService(client=object(), data_engine=_Preferences())
    service.capabilities = _NamingCapabilities()

    try:
        service.save_probe_manny_naming_policy(-1, {}, False)
    except ValueError as error:
        assert "valid probe" in str(error)
    else:
        raise AssertionError("Invalid probe ID should not reach the API.")


def test_apply_existing_breaks_name_swap_conflicts_with_temporary_name():
    preferences = _Preferences()
    service = MissionControlDataService(client=object(), data_engine=preferences)
    service.capabilities = _ConflictNamingCapabilities()

    result = service.save_probe_manny_naming_policy(
        1,
        {
            "enabled": True,
            "mannyTemplate": "Hub - {number}",
            "sequenceStyle": "letters",
        },
        True,
    )

    assert result["renamedMannies"] == 2
    assert result["deferredMannies"] == 0
    assert [item["name"] for item in service.capabilities.manny_rows] == [
        "Hub - A", "Hub - B",
    ]
    assert any("SKW-TMP" in call[2] for call in service.capabilities.renamed_mannies)


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
