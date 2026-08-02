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
    # Completed inventory committed to this goal.  The execution preparer uses
    # these claims to keep lower-priority recipes from consuming assembly parts.
    reserved_items: tuple[tuple[str, int], ...] = ()

    priority: int = 100
