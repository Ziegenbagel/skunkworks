from types import SimpleNamespace

from src.presentation.mission_control import MissionControlViewModelBuilder


def test_movement_view_normalizes_game_transit_fields():
    movement = MissionControlViewModelBuilder._movement_view({
        "movement": {
            "originSector": {"relativeCoordinates": {"x": -6, "y": 7, "z": 5}},
            "arrivalSector": {"relative": {"x": -4, "y": 5, "z": 5}},
            "remainingSeconds": 438,
            "velocityC": 0.23,
            "heading": {"x": 0.7071, "y": -0.7071, "z": 0},
        }
    })
    assert movement["originLabel"] == "-6:7:5"
    assert movement["destinationLabel"] == "-4:5:5"
    assert movement["remainingTime"] == 438
    assert movement["velocity"] == 0.23


def test_communications_counts_all_unread_payload_variants():
    messaging = SimpleNamespace(
        inbox=lambda probe_id: ({"id": 1, "isRead": False}, {"id": 2, "status": "read"}),
        outbox=lambda: ({"id": 3},),
    )
    builder = MissionControlViewModelBuilder(SimpleNamespace(messaging=messaging))
    view = builder._communications({"id": 7})
    assert view["unreadCount"] == 1
    assert len(view["outbox"]) == 1
