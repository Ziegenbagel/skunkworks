"""Task model for the Planner."""

from dataclasses import dataclass

from src.models.galaxy import SectorCoordinates


@dataclass(frozen=True)
class Task:
    """Represents a single action recommended by the Planner."""

    action: str
    reason: str

    category: str = "general"

    target: str | None = None
    quantity: float = 1
    constraints: tuple[str, ...] = ()
    resource_type: str | None = None
    destination: SectorCoordinates | None = None
    route: tuple[SectorCoordinates, ...] = ()
    hazards: tuple[object, ...] = ()

    priority: int = 100
