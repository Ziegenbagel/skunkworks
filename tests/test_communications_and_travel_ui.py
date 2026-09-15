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
    assert movement["arrivalEpochMs"] > 0
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


def test_communications_exposes_typed_probe_and_oracle_recipients():
    messaging = SimpleNamespace(inbox=lambda _probe_id: (), outbox=lambda: ())
    missions = SimpleNamespace(all=lambda: ({
        "name": "Oracle mission", "status": "completed",
        "metadata": {"planetId": "opaque-oracle-id", "planetName": "The Oracle", "sector": {"relative": {"x": 2, "y": 2, "z": 0}}},
    },))
    operations = SimpleNamespace(messaging=messaging, missions=missions)
    world = SimpleNamespace(fleet={"probes": ({"id": 7, "name": "Sender"}, {"id": 8, "name": "Relay"})}, sector={})
    builder = MissionControlViewModelBuilder(operations)

    view = builder._communications({"id": 7, "sector": {"relative": {"x": 2, "y": 2, "z": 0}}}, world)

    assert view["recipients"] == (
        {"type": "probe", "id": 8, "name": "Relay", "label": "Relay"},
        {"type": "planet", "id": "opaque-oracle-id", "name": "The Oracle", "label": "The Oracle · PLANET"},
    )


def test_communications_discovers_new_typed_planet_contacts_from_messages():
    messaging = SimpleNamespace(
        inbox=lambda _probe_id: ({
            "id": "new-contact", "sector": {"relative": {"x": 2, "y": 2, "z": 0}},
            "sender": {"type": "planet", "id": "future-contact", "name": "Archivist"},
        },),
        outbox=lambda: (),
    )
    operations = SimpleNamespace(messaging=messaging, missions=None)
    world = SimpleNamespace(fleet={"probes": ()}, sector={})

    view = MissionControlViewModelBuilder(operations)._communications(
        {"id": 7, "sector": {"relative": {"x": 2, "y": 2, "z": 0}}}, world,
    )

    assert view["recipients"] == ({
        "type": "planet", "id": "future-contact", "name": "Archivist",
        "label": "Archivist · PLANET",
    },)
