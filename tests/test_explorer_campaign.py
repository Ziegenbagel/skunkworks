from types import SimpleNamespace

from src.models.galaxy import GalaxyMap, SectorCoordinates
from src.operations.explorer_campaign import ExplorerCampaignService
from src.planner.desired_state import DesiredState, FuelGoal, ResourceGoal
from src.ui.controller import MissionControlDataService


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


def test_detailed_scan_without_a_fleet_visit_remains_exploration_frontier():
    ops, galaxy = operations()
    scanned = SectorCoordinates(1, 1, 0)
    galaxy.record_observation({"sector": {
        "relativeCoordinates": {"x": scanned.x, "y": scanned.y, "z": scanned.z},
        "knowledgeLevel": "detailed",
        "confidence": 1,
        "objects": [{"id": "planet-1", "type": "planet"}],
    }}, probe_id=44)

    decision = ExplorerCampaignService(ops).decide(mode="any_frontier")

    assert decision.destination == scanned
    assert "scanned but no owned probe has visited" in decision.summary


def test_fleet_visit_removes_even_an_unscanned_sector_from_frontier():
    ops, galaxy = operations()
    visited = SectorCoordinates(-1, -1, 0)
    galaxy.record_visit({
        "relativeCoordinates": {"x": visited.x, "y": visited.y, "z": visited.z},
        "visitCount": 1,
    }, probe_id=81)

    candidates = ExplorerCampaignService(ops).frontier_candidates(
        SectorCoordinates(0, 0, 0),
    )

    assert visited not in {candidate for candidate, _record, _route in candidates}


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


def test_live_current_sector_metal_source_wins_over_missing_map_observation():
    ops, _galaxy = operations()
    ops.mining = SimpleNamespace(
        best_target=lambda resource: {"id": "metal-asteroid", "amount": 1723}
        if resource == "metals" else None,
    )

    decision = ExplorerCampaignService(ops).decide(
        resource_need=("metals", 2),
    )

    assert decision.phase == "resupplying"
    assert decision.destination is None
    assert "global 2 ECE floor" in decision.summary


def test_explorer_treats_display_precision_resource_floor_as_satisfied():
    ops = SimpleNamespace(
        world=SimpleNamespace(probe={
            "fuel": {"deuterium": 20.0, "maxDeuterium": 100.0},
        }),
        probes=SimpleNamespace(fuel_percent=lambda: 20.0),
        mining=SimpleNamespace(active_commitments=lambda: {}),
        inventory=SimpleNamespace(
            reserve_shortages=lambda _goals: {"metals": 0.0},
        ),
    )
    desired = DesiredState(
        fuel=FuelGoal(minimum_percent=20),
        resources=(ResourceGoal("metals", 2),),
    )

    assert MissionControlDataService._explorer_resource_need(ops, desired) is None


def test_explorer_interrupts_only_when_resource_is_genuinely_below_floor():
    ops = SimpleNamespace(
        world=SimpleNamespace(probe={
            "fuel": {"deuterium": 19.99, "maxDeuterium": 100.0},
        }),
        probes=SimpleNamespace(fuel_percent=lambda: 19.99),
        mining=SimpleNamespace(active_commitments=lambda: {}),
        inventory=SimpleNamespace(reserve_shortages=lambda _goals: {}),
    )
    desired = DesiredState(
        fuel=FuelGoal(minimum_percent=20),
        resources=(ResourceGoal("metals", 2),),
    )
    assert MissionControlDataService._explorer_resource_need(ops, desired) == (
        "deuterium", 100.0,
    )

    ops.world.probe["fuel"]["deuterium"] = 20.0
    ops.probes.fuel_percent = lambda: 20.0
    ops.inventory.reserve_shortages = lambda _goals: {"metals": 0.002}
    assert MissionControlDataService._explorer_resource_need(ops, desired) == (
        "metals", 2,
    )
