from src.planner.scheduling import ordered_tasks
from src.planner.task import Task


def test_global_fabrication_priority_precedes_work_tier():
    tasks = ordered_tasks([
        Task("Prepare Probe Assembly", "fleet", category="fleet_assembly", priority=2),
        Task("Craft Item", "Manny target", category="manufacturing", priority=1),
    ])

    assert [(task.category, task.priority) for task in tasks] == [
        ("manufacturing", 1),
        ("fleet_assembly", 2),
    ]


def test_fleet_assembly_breaks_equal_priority_tie():
    tasks = ordered_tasks([
        Task("Craft Item", "Manny target", category="manufacturing", priority=2),
        Task("Prepare Probe Assembly", "fleet", category="fleet_assembly", priority=2),
    ])

    assert [task.category for task in tasks] == ["fleet_assembly", "manufacturing"]


def test_ready_fabrication_stays_ahead_of_higher_priority_mining():
    tasks = ordered_tasks([
        Task("Mine Resource", "dependency", category="mining", priority=1),
        Task("Craft Item", "available craft", category="manufacturing", priority=2),
    ])

    assert [task.category for task in tasks] == ["manufacturing", "mining"]
