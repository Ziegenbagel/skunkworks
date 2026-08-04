"""Cross-goal inventory reservations used by production planning."""

from collections import defaultdict

from src.planner.assembly import tanker_component_statuses


def higher_priority_item_reservations(operations, desired_state, priority):
    """Return completed items committed to higher-priority fleet goals."""

    reserved = defaultdict(int)
    for goal in desired_state.fleet:
        if goal.priority >= priority or goal.model != "deuterium_tanker":
            continue
        current = sum(
            probe.get("model", "generic") == goal.model
            for probe in (getattr(operations.world, "fleet", None) or {}).get("probes", ())
        )
        if current >= goal.quantity:
            continue
        for status in tanker_component_statuses(operations):
            reserved[status["component"]] = max(
                reserved[status["component"]],
                int(status["allocated_stored"]),
            )
    return dict(reserved)


def first_reserved_dependency(operations, recipe_id, reservations):
    """Find the first craftable ingredient unavailable beyond reservations."""

    recipe = operations.manufacturing.recipes.get(recipe_id)
    if recipe is None:
        return None
    for ingredient in recipe.get("ingredients", ()):
        if operations.manufacturing._ingredient_kind(ingredient) != "item":
            continue
        item_type = ingredient["type"]
        required = int(ingredient["quantity"])
        completed_and_active = operations.manufacturing.inventory_count(
            item_type, include_active=True,
        )
        usable = max(
            0,
            completed_and_active - int(reservations.get(item_type, 0)),
        )
        if usable >= required:
            continue
        if operations.manufacturing.recipes.get(item_type) is not None:
            return item_type
    return None
