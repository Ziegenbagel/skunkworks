"""Player-owned goals consumed by planning rules."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProductionGoal:
    """Desired inventory quantity for one craftable item type."""

    recipe_id: str
    quantity: int

    def __post_init__(self):
        if not self.recipe_id:
            raise ValueError("Production goal requires a recipe ID.")

        if self.quantity < 0:
            raise ValueError(
                "Production goal quantity cannot be negative."
            )


@dataclass(frozen=True)
class DesiredState:
    """
    Declarative player goals; intentionally contains no planning logic.
    """

    production: tuple[ProductionGoal, ...] = field(
        default_factory=tuple
    )

    @classmethod
    def empty(cls):
        return cls()
