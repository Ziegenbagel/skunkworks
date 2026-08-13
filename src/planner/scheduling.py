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

# Priority is global within the fabrication stage. This lets a priority-1 Manny
# goal outrank priority-2 fleet assembly, while the tier remains the tie-breaker
# when several goals intentionally share a priority. Acquisition stays behind
# fabrication so dependency/reserve mining cannot consume capacity while any
# craft or assembly command is currently dispatchable.
STAGE_BY_CATEGORY = {
    "safety": 0,
    "inventory": 0,
    "fleet_assembly": 1,
    "manufacturing": 1,
    "transport": 2,
    "travel": 2,
    "fuel": 3,
    "mining": 3,
    "sustainability": 4,
}


def task_order_key(task):
    """Safety, then globally prioritized fabrication, then acquisition."""

    return (
        STAGE_BY_CATEGORY.get(task.category, 2),
        int(task.priority),
        TIER_BY_CATEGORY.get(task.category, 3),
    )


def ordered_tasks(tasks):
    return sorted(tasks, key=task_order_key)
