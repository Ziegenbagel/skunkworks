"""One priority/readiness model shared by planning and execution."""


FABRICATION_ACTIONS = frozenset({
    "Craft Item", "Assemble Probe", "Prepare Manufacturing",
    "Prepare Probe Assembly",
})

TIER_BY_CATEGORY = {
    "safety": 0,
    "inventory": 0,
    "fleet_assembly": 1,
    "manufacturing": 2,
    "transport": 3,
    "travel": 3,
    "fuel": 4,
    "mining": 4,
    "sustainability": 5,
}


def task_order_key(task):
    """Fleet assembly, then production, then acquisition; priority within tier."""

    return (TIER_BY_CATEGORY.get(task.category, 3), int(task.priority))


def ordered_tasks(tasks):
    return sorted(tasks, key=task_order_key)
