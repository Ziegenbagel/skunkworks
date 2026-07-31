"""Task model for the Planner."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    """Represents a single action recommended by the Planner."""

    action: str
    reason: str

    category: str = "general"

    target: str | None = None
    quantity: float = 1
    constraints: tuple[str, ...] = ()

    priority: int = 100
