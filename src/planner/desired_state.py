"""Player-owned goals consumed by planning rules."""

from dataclasses import dataclass, field

from src.models.galaxy import SectorCoordinates


def normalize_priority(value, default=5, legacy=False):
    """Read the 1–10 scale and migrate legacy 1–999 values."""

    if value is None:
        return default
    priority = int(value)
    if legacy:
        priority = max(1, min(10, (priority + 9) // 10))
    return priority


@dataclass(frozen=True)
class ProductionGoal:
    recipe_id: str
    quantity: int
    priority: int = 5

    def __post_init__(self):
        if not self.recipe_id:
            raise ValueError("Production goal requires a recipe ID.")

        if self.quantity < 0:
            raise ValueError(
                "Production goal quantity cannot be negative."
            )
        if not 1 <= self.priority <= 10:
            raise ValueError("Goal priority must be between 1 and 10.")


@dataclass(frozen=True)
class ResourceGoal:
    resource_type: str
    minimum_amount: float
    priority: int = 5

    def __post_init__(self):
        if self.minimum_amount < 0:
            raise ValueError(
                "Resource reserve cannot be negative."
            )
        if not 1 <= self.priority <= 10:
            raise ValueError("Goal priority must be between 1 and 10.")


@dataclass(frozen=True)
class FuelGoal:
    minimum_percent: float = 20
    priority: int = 3

    def __post_init__(self):
        if not 0 <= self.minimum_percent <= 100:
            raise ValueError(
                "Minimum fuel percent must be between 0 and 100."
            )
        if not 1 <= self.priority <= 10:
            raise ValueError("Goal priority must be between 1 and 10.")


@dataclass(frozen=True)
class InventoryGoal:
    minimum_free_capacity: float = 1
    priority: int = 3

    def __post_init__(self):
        if self.minimum_free_capacity < 0:
            raise ValueError(
                "Minimum free capacity cannot be negative."
            )
        if not 1 <= self.priority <= 10:
            raise ValueError("Goal priority must be between 1 and 10.")


@dataclass(frozen=True)
class RepairGoal:
    """Automatic repair policy; a zero trigger disables it."""

    trigger_percent: float = 0
    target_percent: float = 100
    priority: int = 2

    def __post_init__(self):
        if not 0 <= self.trigger_percent <= 99:
            raise ValueError("Repair trigger must be between 0 and 99 percent.")
        if not 1 <= self.target_percent <= 100:
            raise ValueError("Repair target must be between 1 and 100 percent.")
        if self.trigger_percent and self.target_percent <= self.trigger_percent:
            raise ValueError("Repair target must be above the automatic repair trigger.")
        if not 1 <= self.priority <= 10:
            raise ValueError("Goal priority must be between 1 and 10.")


@dataclass(frozen=True)
class TravelGoal:
    target: SectorCoordinates
    route_mode: str = "recommended"

    def __post_init__(self):
        if self.route_mode not in {"recommended", "segmented"}:
            raise ValueError("Travel route mode must be recommended or segmented.")


@dataclass(frozen=True)
class FleetGoal:
    """Desired assembled fleet size by probe model."""

    model: str
    quantity: int
    priority: int = 5

    def __post_init__(self):
        if self.model not in {"generic", "deuterium_tanker"}:
            raise ValueError(f"Unsupported probe model: {self.model}")
        if self.quantity < 0:
            raise ValueError("Fleet goal quantity cannot be negative.")
        if not 1 <= self.priority <= 10:
            raise ValueError("Goal priority must be between 1 and 10.")


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
    repair: RepairGoal = field(default_factory=RepairGoal)
    maximum_mining_order_amount: float = 0.55
    maximum_safe_hop_distance: int = 1
    travel: TravelGoal | None = None
    fleet: tuple[FleetGoal, ...] = field(default_factory=tuple)

    def __post_init__(self):
        amount = float(self.maximum_mining_order_amount)
        if not 0.05 <= amount <= 0.55:
            raise ValueError(
                "Maximum mining order must be between 0.05 and 0.55 ECE."
            )
        steps = amount / 0.05
        if abs(steps - round(steps)) > 0.000001:
            raise ValueError(
                "Maximum mining order must use 0.05 ECE increments."
            )
        if self.maximum_safe_hop_distance not in {1, 2}:
            raise ValueError("Maximum safe hop distance must be 1 or 2 sectors.")

    @classmethod
    def empty(cls):
        return cls()

    @classmethod
    def from_dict(cls, value):
        travel_target = value.get("travelTarget")
        legacy_priorities = value.get("priorityScaleMax") != 10
        return cls(
            production=tuple(
                ProductionGoal(
                    recipe_id=recipe_id,
                    quantity=int(quantity),
                    priority=normalize_priority(value.get("productionPriorities", {}).get(recipe_id), 5, legacy_priorities),
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
                    priority=normalize_priority(goal.get("priority"), 5, legacy_priorities),
                )
                for goal in value.get("production", [])
            ),
            resources=tuple(
                ResourceGoal(
                    resource_type=resource_type,
                    minimum_amount=float(amount),
                    priority=normalize_priority(value.get("resourcePriorities", {}).get(resource_type), 5, legacy_priorities),
                )
                for resource_type, amount in value.get(
                    "resourceReserves",
                    {},
                ).items()
            ),
            fuel=FuelGoal(
                minimum_percent=float(
                    value.get("minimumFuelPercent", 20)
                ),
                priority=normalize_priority(value.get("fuelPriority"), 3, legacy_priorities),
            ),
            inventory=InventoryGoal(
                minimum_free_capacity=float(
                    value.get("minimumFreeCapacity", 1)
                ),
                priority=normalize_priority(value.get("inventoryPriority"), 3, legacy_priorities),
            ),
            repair=RepairGoal(
                trigger_percent=float(value.get("repairTriggerPercent", 0)),
                target_percent=float(value.get("repairTargetPercent", 100)),
                priority=normalize_priority(value.get("repairPriority"), 2, legacy_priorities),
            ),
            maximum_mining_order_amount=float(
                value.get("maximumMiningOrderAmount", 0.55)
            ),
            maximum_safe_hop_distance=int(
                value.get("maximumSafeHopDistance", 1)
            ),
            travel=(
                TravelGoal(
                    target=SectorCoordinates.from_api(
                        travel_target
                    ),
                    route_mode=(
                        value.get("travelRouteMode") or "recommended"
                    ),
                )
                if travel_target is not None
                else None
            ),
            fleet=tuple(
                FleetGoal(
                    model=model,
                    quantity=int(quantity),
                    priority=normalize_priority(value.get("fleetPriorities", {}).get(model), 5, legacy_priorities),
                )
                for model, quantity in value.get("fleetTargets", {}).items()
            ),
        )

    def to_dict(self):
        return {
            "priorityScaleMax": 10,
            "production": [
                {
                    "recipeId": goal.recipe_id,
                    "quantity": goal.quantity,
                    "priority": goal.priority,
                }
                for goal in self.production
            ],
            "resourceReserves": {
                goal.resource_type: goal.minimum_amount
                for goal in self.resources
            },
            "resourcePriorities": {
                goal.resource_type: goal.priority for goal in self.resources
            },
            "minimumFuelPercent": self.fuel.minimum_percent,
            "fuelPriority": self.fuel.priority,
            "minimumFreeCapacity": (
                self.inventory.minimum_free_capacity
            ),
            "inventoryPriority": self.inventory.priority,
            "repairTriggerPercent": self.repair.trigger_percent,
            "repairTargetPercent": self.repair.target_percent,
            "repairPriority": self.repair.priority,
            "maximumMiningOrderAmount": self.maximum_mining_order_amount,
            "maximumSafeHopDistance": self.maximum_safe_hop_distance,
            "travelTarget": (
                {
                    "x": self.travel.target.x,
                    "y": self.travel.target.y,
                    "z": self.travel.target.z,
                }
                if self.travel is not None
                else None
            ),
            "travelRouteMode": (
                self.travel.route_mode
                if self.travel is not None
                else None
            ),
            "fleetTargets": {
                goal.model: goal.quantity for goal in self.fleet
            },
            "fleetPriorities": {
                goal.model: goal.priority for goal in self.fleet
            },
        }
