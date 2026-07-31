"""Player-owned goals consumed by planning rules."""

from dataclasses import dataclass, field

from src.models.galaxy import SectorCoordinates


@dataclass(frozen=True)
class ProductionGoal:
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
class ResourceGoal:
    resource_type: str
    minimum_amount: float

    def __post_init__(self):
        if self.minimum_amount < 0:
            raise ValueError(
                "Resource reserve cannot be negative."
            )


@dataclass(frozen=True)
class FuelGoal:
    minimum_percent: float = 20

    def __post_init__(self):
        if not 0 <= self.minimum_percent <= 100:
            raise ValueError(
                "Minimum fuel percent must be between 0 and 100."
            )


@dataclass(frozen=True)
class InventoryGoal:
    minimum_free_capacity: float = 1

    def __post_init__(self):
        if self.minimum_free_capacity < 0:
            raise ValueError(
                "Minimum free capacity cannot be negative."
            )


@dataclass(frozen=True)
class TravelGoal:
    target: SectorCoordinates


@dataclass(frozen=True)
class DesiredState:
    """Declarative player goals with no planning logic."""

    production: tuple[ProductionGoal, ...] = field(
        default_factory=tuple
    )
    resources: tuple[ResourceGoal, ...] = field(
        default_factory=tuple
    )
    fuel: FuelGoal = field(default_factory=FuelGoal)
    inventory: InventoryGoal = field(
        default_factory=InventoryGoal
    )
    travel: TravelGoal | None = None

    @classmethod
    def empty(cls):
        return cls()

    @classmethod
    def from_dict(cls, value):
        travel_target = value.get("travelTarget")
        return cls(
            production=tuple(
                ProductionGoal(
                    recipe_id=recipe_id,
                    quantity=int(quantity),
                )
                for recipe_id, quantity in value.get(
                    "production",
                    {},
                ).items()
            )
            if isinstance(value.get("production"), dict)
            else tuple(
                ProductionGoal(
                    recipe_id=goal["recipeId"],
                    quantity=int(goal["quantity"]),
                )
                for goal in value.get("production", [])
            ),
            resources=tuple(
                ResourceGoal(
                    resource_type=resource_type,
                    minimum_amount=float(amount),
                )
                for resource_type, amount in value.get(
                    "resourceReserves",
                    {},
                ).items()
            ),
            fuel=FuelGoal(
                minimum_percent=float(
                    value.get("minimumFuelPercent", 20)
                )
            ),
            inventory=InventoryGoal(
                minimum_free_capacity=float(
                    value.get("minimumFreeCapacity", 1)
                )
            ),
            travel=(
                TravelGoal(
                    target=SectorCoordinates.from_api(
                        travel_target
                    )
                )
                if travel_target is not None
                else None
            ),
        )

    def to_dict(self):
        return {
            "production": [
                {
                    "recipeId": goal.recipe_id,
                    "quantity": goal.quantity,
                }
                for goal in self.production
            ],
            "resourceReserves": {
                goal.resource_type: goal.minimum_amount
                for goal in self.resources
            },
            "minimumFuelPercent": self.fuel.minimum_percent,
            "minimumFreeCapacity": (
                self.inventory.minimum_free_capacity
            ),
            "travelTarget": (
                {
                    "x": self.travel.target.x,
                    "y": self.travel.target.y,
                    "z": self.travel.target.z,
                }
                if self.travel is not None
                else None
            ),
        }
