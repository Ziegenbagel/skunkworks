"""Task model for the Planner."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    """Represents a single action recommended by the Planner."""

    category: str
    action: str
    target: str | None = None
    quantity: int = 1
    priority: int = 0
    reason: str = ""