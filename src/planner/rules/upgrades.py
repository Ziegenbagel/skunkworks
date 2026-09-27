"""Mine, manufacture, then install one explicitly selected improvement."""
from dataclasses import replace
from math import ceil

from src.operations.upgrades import UpgradeService
from src.planner.desired_state import DesiredState, ResourceGoal
from src.planner.task import Task
from src.planner.rules import mining


def plan(operations, desired_state):
    goal = desired_state.upgrade
    if goal is None:
        return []
    view = UpgradeService(operations).assess(goal)
    metadata = {"upgradeScope": goal.scope, "upgradeGoal": {
        "improvementId": goal.improvement_id, "scope": goal.scope, "priority": goal.priority}}
    parent = Task(action="Prepare Probe Upgrade", reason=view["name"] + ": " + view["summary"],
        category="upgrade", target=goal.improvement_id, priority=goal.priority,
        constraints=tuple(view["blockers"] or ("upgrade_" + view["status"],)), metadata=metadata)
    if view["status"] == "complete":
        return []
    if view["status"] == "ready":
        return [replace(parent, action="Install Probe Upgrade", constraints=(), workflow_authorized=True)]
    if view["status"] in {"installing", "blocked", "waiting"}:
        return [parent]
    tasks = [parent]
    required_resources = dict(view["resources"])
    # Build consumers before their ingredients so the final direct-input kit
    # converges even when the server spends stored components recursively.
    def depth(recipe_id, ancestors=frozenset()):
        if recipe_id in ancestors:
            return 0
        recipe = operations.manufacturing.recipes.get(recipe_id) or {}
        return 1 + max((depth(row["type"], ancestors | {recipe_id})
            for row in recipe.get("ingredients", ()) if row.get("kind") == "item"), default=0)
    missing = sorted(view["missingItems"], key=lambda key: (-depth(key), key))
    if missing:
        component = missing[0]
        production = operations.manufacturing.production_plan(component, use_inventory_items=True)
        if production is None:
            tasks[0] = replace(parent, constraints=("unknown_upgrade_component_recipe",))
        else:
            for resource, amount in production["required_resources"].items():
                required_resources[resource] = required_resources.get(resource, 0) + amount
            available, _ = operations.manufacturing.available_inputs()
            blockers = list(production["blockers"])
            if any(available.get(key, 0) + 0.00001 < amount for key, amount in required_resources.items()):
                blockers.append("missing_resources")
            tasks.append(Task(action="Craft Item" if not blockers else "Prepare Manufacturing",
                reason=f"Prepare {component.replace('_', ' ')} for {view['name']}; upgrade stock is protected.",
                category="upgrade", target=component, quantity=view["missingItems"][component],
                priority=goal.priority, constraints=tuple(dict.fromkeys(blockers)),
                workflow_authorized=True, metadata=metadata))
    available, _ = operations.manufacturing.available_inputs()
    # Round acquisition up to a deliverable amount; a sub-milli-ECE shortage
    # must not disappear in the generic reserve planner's display rounding.
    rounded_requirements = {}
    for resource, required in required_resources.items():
        scale = 100 if resource == "deuterium" else 1
        step = 0.01 if resource == "deuterium" else 0.001
        stored = available.get(resource, 0) * scale
        deficit = max(0, required * scale - stored)
        rounded_requirements[resource] = stored + ceil(deficit / step - 1e-9) * step
    mining_state = replace(DesiredState.unconfigured(),
        maximum_mining_order_amount=desired_state.maximum_mining_order_amount,
        resources=tuple(ResourceGoal(key, value, goal.priority)
                        for key, value in rounded_requirements.items()))
    for task in mining.plan(operations, mining_state):
        tasks.append(replace(task, background_work=False, workflow_authorized=True,
            reason=f"Supply {view['name']}. " + task.reason,
            metadata={**metadata, "forceProbeStorage": True}))
    return tasks
