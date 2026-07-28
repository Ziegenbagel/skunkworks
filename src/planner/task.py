"""Task model for the Planner."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    """Represents a single action recommended by the Planner."""

    action: str
    reason: str

    category: str = "general"

    target: str | None = None
    quantity: int = 1

    priority: int = 100