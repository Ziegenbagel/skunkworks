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
    # Per-dispatch cap. The task quantity remains the full uncovered need so
    # planning explanations and remaining-amount accounting stay accurate.
    maximum_order_amount: float = 0.55
    # Reserve-floor replenishment is useful background work, but it must not
    # occupy the whole Manny workforce and prevent fabrication from resuming.
    background_work: bool = False
    destination: SectorCoordinates | None = None
    route: tuple[SectorCoordinates, ...] = ()
    hazards: tuple[object, ...] = ()
    # Automatic travel may only dispatch along a fully verified SCUT route.
    require_scut_coverage: bool = False
    # Consent applies to this unchanged durable auto-travel goal, rather than
    # being requested again for every generated segment fingerprint.
    risk_acknowledged: bool = False
    # Durable workflows may intentionally issue the same game mutation again
    # in a later cycle.  This scope separates those cycles while preserving
    # duplicate protection for retries within the current workflow step.
    idempotency_scope: str | None = None
    # Completed inventory committed to this goal.  The execution preparer uses
    # these claims to keep lower-priority recipes from consuming assembly parts.
    reserved_items: tuple[tuple[str, int], ...] = ()

    priority: int = 100
