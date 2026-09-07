from types import SimpleNamespace

from src.models.galaxy import GalaxyMap, SectorCoordinates
from src.operations.explorer_campaign import ExplorerCampaignService


class Travel:
    def __init__(self, current):
        self.current = current

    def current_sector(self):
        return self.current

    def route_to(self, target):
        return (target,)


class Safety:
    def __init__(self, blocked=()):
        self.blocked = set(blocked)

    def scut_route_covered(self, _origin, route):
        return not any(point in self.blocked for point in route)


def operations(*, objects=(), blocked=()):
    current = SectorCoordinates(0, 0, 0)
    galaxy = GalaxyMap()
    galaxy.record_visit({
        "relativeCoordinates": {"x": 0, "y": 0, "z": 0}, "visitCount": 1,
    })
    return SimpleNamespace(
        travel=Travel(current),
        travel_safety=Safety(blocked),
        galaxy=SimpleNamespace(known_sectors=galaxy.sectors),
        world=SimpleNamespace(sector={"snapshot": {"sector": {"objects": objects}}}),
    ), galaxy


def test_planetary_focus_prefers_planet_evidence_but_falls_back():
    ops, galaxy = operations()
    ordinary = {"sector": {"relativeCoordinates": {"x": 1, "y": 1, "z": 0}}}
    planetary = {"sector": {
        "relativeCoordinates": {"x": 1, "y": 0, "z": 1},
        "estimatedObjects": {"planetCountMax": 3},
    }}
    galaxy.record_observation(ordinary)
    galaxy.record_observation(planetary)
    decision = ExplorerCampaignService(ops).decide(mode="planetary_frontier")
    assert decision.destination == SectorCoordinates(1, 0, 1)

    ops, _galaxy = operations(blocked={SectorCoordinates(1, 0, 1)})
    fallback = ExplorerCampaignService(ops).decide(mode="planetary_frontier")
    assert fallback.destination is not None
    assert "nearest frontier" in fallback.summary


def test_frontier_never_selects_a_route_without_verified_scut_coverage():
    neighbors = set(SectorCoordinates(0, 0, 0).neighbors())
    ops, _galaxy = operations(blocked=neighbors)
    decision = ExplorerCampaignService(ops).decide()
    assert decision.destination is None
    assert decision.phase == "waiting"


def test_construct_and_others_wreck_create_real_manny_inspection_tasks():
    ops, _galaxy = operations(objects=(
        {"id": "construct-7", "type": "dormant_construct", "name": "Artifact"},
        {"id": "wreck-2", "type": "others_mothership_wreck"},
    ))
    decision = ExplorerCampaignService(ops).decide()
    assert decision.phase == "inspecting"
    assert [task.action for task in decision.tasks] == [
        "Inspect Sector Object", "Inspect Sector Object",
    ]
    assert all(task.workflow_authorized for task in decision.tasks)


def test_camel_case_construct_and_derelict_others_ship_are_inspected():
    ops, _galaxy = operations(objects=(
        {"id": "construct-8", "type": "dormantConstruct"},
        {"id": "ship-3", "type": "ship", "observedClass": "others", "status": "derelict"},
    ))
    decision = ExplorerCampaignService(ops).decide()
    assert {task.target for task in decision.tasks} == {"construct-8", "ship-3"}


def test_unacknowledged_civilization_contact_is_a_hard_pause():
    ops, _galaxy = operations()
    decision = ExplorerCampaignService(ops).decide(alerts=(
        {"id": 9, "summary": "Habitable species discovered", "status": "unread"},
    ))
    assert decision.phase == "contact_hold"
    assert decision.paused is True
    acknowledged = ExplorerCampaignService(ops).decide(alerts=(
        {"id": 9, "summary": "Habitable species discovered", "status": "read"},
    ))
    assert acknowledged.phase == "travelling"


def test_global_resource_floor_redirects_explorer_to_known_scut_source():
    ops, galaxy = operations()
    galaxy.record_observation({"sector": {
        "relativeCoordinates": {"x": 1, "y": 1, "z": 0},
        "objects": [{"id": "ice", "resources": {"deuterium": 20}}],
    }})
    decision = ExplorerCampaignService(ops).decide(resource_need=("deuterium", 100))
    assert decision.phase == "resupply_travel"
    assert decision.destination == SectorCoordinates(1, 1, 0)
