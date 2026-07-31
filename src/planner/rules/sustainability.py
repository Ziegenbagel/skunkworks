"""Finite-resource continuity planning."""

from src.planner.priorities import HIGH, INFO, NORMAL
from src.planner.task import Task


def plan(operations) -> list[Task]:
    report = operations.resource_sustainability.report()
    tasks = []

    for warning in report.warnings:
        if warning.code == "finite_wandering_asteroid_field":
            tasks.append(
                Task(
                    action="Monitor Finite Asteroid Field",
                    reason=warning.message,
                    category="sustainability",
                    target="Current Sector",
                    priority=INFO,
                )
            )
            continue

        replacement = next(
            (
                source
                for source in report.replacements
                if source.resource_type
                == warning.resource_type
            ),
            None,
        )
        tasks.append(
            Task(
                action=(
                    "Prepare Replacement Resource Source"
                    if replacement is not None
                    else "Search for Replacement Resources"
                ),
                reason=warning.message,
                category="sustainability",
                target=(
                    (
                        f"{replacement.coordinates.x}:"
                        f"{replacement.coordinates.y}:"
                        f"{replacement.coordinates.z}"
                    )
                    if replacement is not None
                    else warning.resource_type
                ),
                resource_type=warning.resource_type,
                priority=(
                    HIGH
                    if warning.severity == "critical"
                    else NORMAL
                ),
            )
        )

    for logistics in report.logistics_plans:
        tasks.append(
            Task(
                action="Stage Resource Logistics",
                reason=logistics.summary,
                category="logistics",
                target=logistics.resource_type,
                constraints=(
                    "fleet_role_assignment_not_automated",
                ),
                resource_type=logistics.resource_type,
                priority=NORMAL,
            )
        )

    return tasks
