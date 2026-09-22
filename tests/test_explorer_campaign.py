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
        route = []
        current = self.current
        while current != target:
            distance = current.distance_to(target)
            current = min(
                (point for point in current.neighbors()
                 if point.distance_to(target) < distance),
                key=lambda point: (point.distance_to(target), point.x, point.y, point.z),
            )
            route.append(current)
        return tuple(route)

    @staticmethod
    def fuel_cost():
        return 2


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
        world=SimpleNamespace(
            probe={"fuel": {"deuterium": 50, "maxDeuterium": 100}},
            sector={"snapshot": {"sector": {"objects": objects}}},
        ),
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


def test_completed_construct_inspection_resumes_frontier_selection():
    ops, _galaxy = operations(objects=(
        {"id": "construct-7", "type": "dormant_construct", "name": "Artifact"},
    ))

    decision = ExplorerCampaignService(ops).decide(
        completed_inspections={"construct-7"},
    )

    assert decision.phase == "travelling"
    assert decision.destination is not None


def test_active_construct_inspection_does_not_assign_another_manny():
    ops, _galaxy = operations(objects=(
        {"id": "construct-7", "type": "dormant_construct", "name": "Artifact"},
    ))
    ops.world.mannies = {"mannies": [{
        "id": "manny-1",
        "currentTask": {
            "type": "inspect-sector-object",
            "payload": {"objectId": "construct-7"},
        },
    }]}

    decision = ExplorerCampaignService(ops).decide()

    assert decision.phase == "inspecting"
    assert "active Manny" in decision.summary
    assert not decision.tasks


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


def test_fuel_floor_redirects_only_to_source_reachable_on_remaining_reserve():
    ops, galaxy = operations()
    ops.world.probe["fuel"]["deuterium"] = 2
    reachable = SectorCoordinates(1, 1, 0)
    galaxy.record_observation({"sector": {
        "relativeCoordinates": {"x": reachable.x, "y": reachable.y, "z": reachable.z},
        "objects": [{"resources": {"deuterium": 20}}],
    }})

    decision = ExplorerCampaignService(ops).decide(
        resource_need=("deuterium", 100),
    )

    assert decision.phase == "resupply_travel"
    assert decision.destination == reachable


def test_unreachable_deuterium_source_pauses_for_manual_refueling():
    ops, galaxy = operations()
    ops.world.probe["fuel"]["deuterium"] = 2
    unreachable = SectorCoordinates(2, 2, 0)
    galaxy.record_observation({"sector": {
        "relativeCoordinates": {
            "x": unreachable.x, "y": unreachable.y, "z": unreachable.z,
        },
        "objects": [{"resources": {"deuterium": 20}}],
    }})

    decision = ExplorerCampaignService(ops).decide(
        resource_need=("deuterium", 100),
    )

    assert decision.phase == "fuel_resupply_manual_hold"
    assert decision.paused is True
    assert decision.destination is None
    assert "manual refueling operations" in decision.summary


def test_resupply_route_recognizes_modern_nested_resource_observations():
    ops, galaxy = operations()
    modern_source = SectorCoordinates(1, 1, 0)
    galaxy.record_observation({"sector": {
        "relativeCoordinates": {
            "x": modern_source.x, "y": modern_source.y, "z": modern_source.z,
        },
        "objects": [{
            "id": "system-1", "type": "solar_system",
            "minableTargets": [{
                "id": "metal-1", "type": "asteroid",
                "resourceTypes": ["metals"],
                "resourceAmounts": {"metals": 18.5},
            }],
        }],
    }})

    decision = ExplorerCampaignService(ops).decide(
        resource_need=("metals", 2),
    )

    assert decision.phase == "resupply_travel"
    assert decision.destination == modern_source


def test_resupply_route_ignores_depleted_modern_resource_observation():
    ops, galaxy = operations()
    galaxy.record_observation({"sector": {
        "relativeCoordinates": {"x": 1, "y": 1, "z": 0},
        "objects": [{
            "id": "metal-1", "type": "asteroid",
            "resourceTypes": ["metals"],
            "resourceAmounts": {"metals": 0},
        }],
    }})

    decision = ExplorerCampaignService(ops).decide(
        resource_need=("metals", 2),
    )

    assert decision.phase == "resupply_wait"
    assert decision.destination is None


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


def test_explorer_treats_projected_arrival_at_fuel_floor_as_satisfied():
    ops = SimpleNamespace(
        world=SimpleNamespace(probe={
            "fuel": {"deuterium": 22.0, "maxDeuterium": 100.0},
        }),
        travel=SimpleNamespace(fuel_cost=lambda: 2.0),
        probes=SimpleNamespace(fuel_percent=lambda: 22.0),
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


def test_explorer_interrupts_before_next_leg_would_cross_fuel_floor():
    ops = SimpleNamespace(
        world=SimpleNamespace(probe={
            "fuel": {"deuterium": 21.99, "maxDeuterium": 100.0},
        }),
        travel=SimpleNamespace(fuel_cost=lambda: 2.0),
        probes=SimpleNamespace(fuel_percent=lambda: 21.99),
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

    ops.world.probe["fuel"]["deuterium"] = 22.0
    ops.probes.fuel_percent = lambda: 22.0
    ops.inventory.reserve_shortages = lambda _goals: {"metals": 0.002}
    assert MissionControlDataService._explorer_resource_need(ops, desired) == (
        "metals", 2,
    )
