"""Resource-reserve and manufacturing-shortage mining planning."""

from collections import defaultdict

from src.planner.priorities import HIGH, NORMAL
from src.planner.task import Task
from src.planner.assembly import tanker_component_statuses


def plan(operations, desired_state, *, dependency_lookahead=False) -> list[Task]:
    reserve_shortages = operations.inventory.reserve_shortages(
        desired_state.resources
    )
    shortages = dict(reserve_shortages)
    manufacturing_resources = set()
    resource_reasons = defaultdict(set)
    fabrication_dependencies = defaultdict(list)
    priorities = {
        goal.resource_type: goal.priority
        for goal in desired_state.resources
    }
    for goal in desired_state.resources:
        resource_reasons[goal.resource_type].add(
            f"the {goal.minimum_amount:g} {goal.resource_type.replace('_', ' ')} reserve target"
        )

    for goal in desired_state.production:
        current = operations.manufacturing.inventory_count(
            goal.recipe_id
        )
        shortage = max(0, goal.quantity - current)

        if shortage <= 0:
            continue

        # Normal planning funds only the next craft.  The controller may opt
        # into a larger horizon after Mannys have remained idle through its
        # grace period, but only when that next craft is genuinely blocked on
        # raw resources.  If one unit is already craftable, manufacturing must
        # consume those inputs and replan before mining for later units.  This
        # prevents a large production target from continuously sending spare
        # Mannys mining even though the immediate craft is ready.
        next_unit = operations.manufacturing.production_plan(
            goal.recipe_id,
            quantity=1,
            include_operational_constraints=False,
            use_inventory_items=False,
        )
        if next_unit is None or not next_unit["missing_resources"]:
            continue
        production = operations.manufacturing.production_plan(
            goal.recipe_id,
            quantity=shortage if dependency_lookahead else 1,
            include_operational_constraints=False,
            use_inventory_items=False,
        )

        if production is None:
            continue

        for resource_type, amount in production[
            "missing_resources"
        ].items():
            fabrication_dependencies[resource_type].append(
                (goal.priority, float(amount),
                 (
                     "remaining production target: "
                     if dependency_lookahead
                     else "next production unit: "
                 ) + goal.recipe_id.replace("_", " "))
            )

    for goal in desired_state.fleet:
        if goal.model != "deuterium_tanker":
            continue
        current_fleet = sum(
            probe.get("model", "generic") == goal.model
            for probe in (getattr(operations.world, "fleet", None) or {}).get("probes", ())
        )
        if current_fleet >= goal.quantity:
            continue
        requests = {
            status["component"]: status["missing"]
            for status in tanker_component_statuses(operations)
            if status["missing"] > 0
        }
        for component, quantity in requests.items():
            component_plan = operations.manufacturing.production_plan(
                component,
                quantity=quantity,
                include_operational_constraints=False,
                use_inventory_items=False,
            )
            if component_plan is None:
                continue
            for resource_type, amount in component_plan["missing_resources"].items():
                if amount > 0:
                    fabrication_dependencies[resource_type].append(
                        (goal.priority, float(amount),
                         f"tanker component: {component.replace('_', ' ')}")
                    )

    # Fund only the highest-priority blocked fabrication horizon for each raw
    # resource. Do not relabel a large lower-priority reserve floor (or every
    # lower-priority recipe) as priority 1 merely because they share metals.
    # The next refresh rebuilds the selected horizon from current inventory
    # and active production, then advances once that need is covered.
    for resource_type, dependencies in fabrication_dependencies.items():
        leading_priority = min(priority for priority, _amount, _reason in dependencies)
        leading = [item for item in dependencies if item[0] == leading_priority]
        shortages[resource_type] = max(amount for _priority, amount, _reason in leading)
        resource_reasons[resource_type] = {
            reason for _priority, _amount, reason in leading
        }
        priorities[resource_type] = leading_priority
        manufacturing_resources.add(resource_type)

    tasks = []
    active_commitments = operations.mining.active_commitments()
    current_sector = operations.travel.current_sector()
    hazardous_stop = (
        current_sector is not None
        and operations.travel_safety.is_black_hole_sector(current_sector)
    )

    for resource_type, amount in shortages.items():
        committed = float(active_commitments.get(resource_type, 0))
        uncovered_amount = max(0, float(amount) - committed)
        if uncovered_amount <= 0.00001:
            continue
        target = operations.mining.best_target(resource_type)
        constraints = []

        if hazardous_stop:
            constraints.append("black_hole_sector_unsafe_for_mining")

        if target is None:
            constraints.append("resource_not_in_current_sector")

        if not operations.mining.idle_mannies():
            constraints.append("no_idle_manny")

        if operations.world.probe["status"] != "idle":
            constraints.append("probe_unavailable")

        free_capacity = operations.inventory.mining_return_capacity(
            active_commitments
        )
        if resource_type != "deuterium" and free_capacity <= 0:
            constraints.append("insufficient_probe_storage")

        order_amount = uncovered_amount
        if target is not None:
            order_amount = min(order_amount, target.get("available_amount", order_amount))
        if resource_type != "deuterium":
            order_amount = min(order_amount, free_capacity)

        reasons = sorted(resource_reasons.get(resource_type, ()))
        purpose = (
            "; ".join(reasons)
            if reasons
            else "the highest-priority unmet goal"
        )
        background_work = resource_type not in manufacturing_resources
        tasks.append(
            Task(
                action=(
                    "Mine Resource"
                    if not constraints
                    else "Locate Mining Opportunity"
                ),
                reason=(
                    f"Need {amount:.3f} additional {resource_type.replace('_', ' ')}; "
                    f"{committed:.3f} is already committed to active mining and "
                    f"{uncovered_amount:.3f} remains uncovered. "
                    f"This mining order unlocks {purpose}."
                    + (
                        " Reserve-floor mining runs as background work so "
                        "fabrication capacity remains available."
                        if background_work else ""
                    )
                ),
                category="mining",
                target=(
                    target["id"]
                    if target is not None
                    else resource_type
                ),
                quantity=round(order_amount, 3),
                maximum_order_amount=desired_state.maximum_mining_order_amount,
                background_work=background_work,
                constraints=tuple(constraints),
                resource_type=resource_type,
                priority=priorities.get(
                    resource_type,
                    HIGH if resource_type in manufacturing_resources else NORMAL,
                ),
            )
        )

    # Equal-priority resource orders are balanced by current active coverage.
    # This prevents the first resource in saved settings from claiming every
    # newly-idle Manny while other requirements remain completely uncovered.
    tasks.sort(key=lambda task: (
        task.priority,
        active_commitments.get(task.resource_type, 0)
        / max(float(shortages.get(task.resource_type, 0)), 0.00001),
        -float(shortages.get(task.resource_type, 0)),
    ))
    return tasks
