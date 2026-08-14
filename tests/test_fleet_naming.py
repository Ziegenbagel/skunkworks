from src.ui.controller import MissionControlController, MissionControlDataService


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
