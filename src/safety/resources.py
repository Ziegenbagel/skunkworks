"""Finite-resource warnings and replacement-source planning."""

import json
from dataclasses import dataclass
from pathlib import Path

from src.models.galaxy import SectorCoordinates


@dataclass(frozen=True)
class ResourceSafetyPolicy:
    warn_on_low_asteroids: bool = True
    warn_on_finite_wandering_fields: bool = True
    low_remaining_percent: float = 25
    critical_remaining_percent: float = 10
    minimum_absolute_amount: float = 0.25
    replacement_minimum_amount: float = 1
    replacement_candidate_limit: int = 5
    plan_transport_logistics: bool = True

    @classmethod
    def from_dict(cls, value):
        policy = cls(
            warn_on_low_asteroids=bool(
                value.get("warnOnLowAsteroids", True)
            ),
            warn_on_finite_wandering_fields=bool(
                value.get(
                    "warnOnFiniteWanderingFields",
                    True,
                )
            ),
            low_remaining_percent=float(
                value.get("lowRemainingPercent", 25)
            ),
            critical_remaining_percent=float(
                value.get("criticalRemainingPercent", 10)
            ),
            minimum_absolute_amount=float(
                value.get("minimumAbsoluteAmount", 0.25)
            ),
            replacement_minimum_amount=float(
                value.get("replacementMinimumAmount", 1)
            ),
            replacement_candidate_limit=int(
                value.get("replacementCandidateLimit", 5)
            ),
            plan_transport_logistics=bool(
                value.get("planTransportLogistics", True)
            ),
        )

        if not (
            0
            <= policy.critical_remaining_percent
            <= policy.low_remaining_percent
            <= 100
        ):
            raise ValueError(
                "Resource warning percentages must satisfy "
                "0 <= critical <= low <= 100."
            )

        if (
            policy.minimum_absolute_amount < 0
            or policy.replacement_minimum_amount < 0
            or policy.replacement_candidate_limit < 1
        ):
            raise ValueError(
                "Resource amounts must be non-negative and "
                "candidate limit must be positive."
            )

        return policy


@dataclass(frozen=True)
class ResourceWarning:
    code: str
    severity: str
    object_id: str
    resource_type: str | None
    message: str
    current_amount: float | None = None
    baseline_amount: float | None = None
    remaining_percent: float | None = None


@dataclass(frozen=True)
class ReplacementSource:
    coordinates: SectorCoordinates
    object_id: str
    resource_type: str
    amount: float
    distance: int
    observed_at: str


@dataclass(frozen=True)
class FleetRoleRequirement:
    role: str
    count: int
    sector: SectorCoordinates
    reason: str


@dataclass(frozen=True)
class ResourceLogisticsPlan:
    resource_type: str
    hub_sector: SectorCoordinates
    source: ReplacementSource
    roles: tuple[FleetRoleRequirement, ...]
    summary: str


@dataclass(frozen=True)
class ResourceSustainabilityReport:
    warnings: tuple[ResourceWarning, ...]
    replacements: tuple[ReplacementSource, ...]
    logistics_plans: tuple[ResourceLogisticsPlan, ...]
    wandering_asteroid_count: int
    wandering_generation_maximum: int = 5
    replenishment_observed: bool = False


class ResourceSustainabilityService:
    WANDERING_GENERATION_MAXIMUM = 5

    def __init__(self, world, data_engine, policy):
        self.world = world
        self.data_engine = data_engine
        self.policy = policy

    def report(self):
        current_sector = self._current_sector()

        if current_sector is None:
            return ResourceSustainabilityReport(
                warnings=(),
                replacements=(),
                logistics_plans=(),
                wandering_asteroid_count=0,
            )

        warnings = list(self._resource_warnings(current_sector))
        wandering_count = self._wandering_count()

        if (
            self.policy.warn_on_finite_wandering_fields
            and wandering_count > 0
        ):
            warnings.append(
                ResourceWarning(
                    code="finite_wandering_asteroid_field",
                    severity="info",
                    object_id="current-sector",
                    resource_type=None,
                    message=(
                        f"Sector contains {wandering_count} "
                        "wandering asteroid(s). Generation creates "
                        "at most five and no replenishment path is "
                        "present in the reviewed game rules."
                    ),
                )
            )

        resource_types = tuple(
            dict.fromkeys(
                warning.resource_type
                for warning in warnings
                if warning.resource_type is not None
                and warning.severity in {"warning", "critical"}
            )
        )
        replacements = tuple(
            source
            for resource_type in resource_types
            for source in self.replacement_sources(
                resource_type,
                current_sector,
            )
        )
        plans = tuple(
            self._logistics_plan(
                resource_type,
                current_sector,
                replacements,
            )
            for resource_type in resource_types
            if any(
                source.resource_type == resource_type
                for source in replacements
            )
            and self.policy.plan_transport_logistics
        )

        return ResourceSustainabilityReport(
            warnings=tuple(warnings),
            replacements=replacements,
            logistics_plans=plans,
            wandering_asteroid_count=wandering_count,
        )

    def replacement_sources(
        self,
        resource_type,
        origin=None,
    ):
        if self.data_engine is None:
            return ()

        origin = origin or self._current_sector()

        if origin is None:
            return ()

        rows = self.data_engine.latest_resource_sources(
            resource_type,
            minimum_amount=self.policy.replacement_minimum_amount,
        )
        sources = []

        for row in rows:
            coordinates = SectorCoordinates(
                row["sector_x"],
                row["sector_y"],
                row["sector_z"],
            )

            if coordinates == origin:
                continue

            sources.append(
                ReplacementSource(
                    coordinates=coordinates,
                    object_id=row["object_id"],
                    resource_type=resource_type,
                    amount=row["amount"],
                    distance=origin.distance_to(coordinates),
                    observed_at=row["observed_at"],
                )
            )

        return tuple(
            sorted(
                sources,
                key=lambda source: (
                    source.distance,
                    -source.amount,
                    source.coordinates,
                ),
            )[: self.policy.replacement_candidate_limit]
        )

    def _resource_warnings(self, sector):
        if not self.policy.warn_on_low_asteroids:
            return ()

        warnings = []

        for target in self.world.sector.get("resources", []):
            for resource_type, current in target.get(
                "resources",
                {},
            ).items():
                baseline = self._baseline(
                    sector,
                    target["id"],
                    resource_type,
                    current,
                )

                if baseline <= 0:
                    continue

                remaining = (
                    current / baseline * 100
                    if baseline > 0
                    else 0
                )
                absolute_low = (
                    current
                    <= self.policy.minimum_absolute_amount
                )

                if (
                    remaining
                    <= self.policy.critical_remaining_percent
                    or current <= 0
                ):
                    severity = "critical"
                elif (
                    remaining
                    <= self.policy.low_remaining_percent
                    or absolute_low
                ):
                    severity = "warning"
                else:
                    continue

                warnings.append(
                    ResourceWarning(
                        code="asteroid_resource_low",
                        severity=severity,
                        object_id=target["id"],
                        resource_type=resource_type,
                        current_amount=round(current, 4),
                        baseline_amount=round(baseline, 4),
                        remaining_percent=round(remaining, 1),
                        message=(
                            f"{resource_type.replace('_', ' ')} "
                            f"on {target['id']} has {current:.3f} "
                            f"ECE remaining ({remaining:.1f}% of "
                            "the highest observed amount)."
                        ),
                    )
                )

        return tuple(warnings)

    def _baseline(
        self,
        sector,
        object_id,
        resource_type,
        current,
    ):
        if self.data_engine is None:
            return current

        rows = self.data_engine.resource_source_history(
            sector,
            object_id,
            resource_type,
        )
        return max(
            [current, *(row["amount"] for row in rows)],
            default=current,
        )

    def _wandering_count(self):
        snapshot = self.world.sector.get("snapshot") or {}
        return sum(
            1
            for object_ in snapshot.get("sector", {}).get(
                "objects",
                [],
            )
            if object_.get("mannyMineable", False)
        )

    def _current_sector(self):
        sector = self.world.probe.get("sector") or {}
        relative = sector.get("relative")
        return (
            SectorCoordinates.from_api(relative)
            if relative is not None
            else None
        )

    def _logistics_plan(
        self,
        resource_type,
        hub_sector,
        replacements,
    ):
        source = next(
            replacement
            for replacement in replacements
            if replacement.resource_type == resource_type
        )
        return ResourceLogisticsPlan(
            resource_type=resource_type,
            hub_sector=hub_sector,
            source=source,
            roles=(
                FleetRoleRequirement(
                    role="hub",
                    count=1,
                    sector=hub_sector,
                    reason=(
                        "Maintain production and receive imported "
                        "resources."
                    ),
                ),
                FleetRoleRequirement(
                    role="miner",
                    count=1,
                    sector=source.coordinates,
                    reason=(
                        "Remain with the replacement deposit and "
                        "operate the mining site."
                    ),
                ),
                FleetRoleRequirement(
                    role="transport",
                    count=1,
                    sector=hub_sector,
                    reason=(
                        "Shuttle resources between the source and "
                        "hub; assignment is deferred until fleet "
                        "logistics automation."
                    ),
                ),
            ),
            summary=(
                f"Establish {resource_type.replace('_', ' ')} "
                f"mining at {self._label(source.coordinates)} and "
                f"transport output to hub {self._label(hub_sector)}."
            ),
        )

    def _label(self, coordinates):
        return (
            f"{coordinates.x}:{coordinates.y}:{coordinates.z}"
        )


class ResourceSafetyPolicyStore:
    def __init__(
        self,
        path="config/resource_safety.json",
    ):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return ResourceSafetyPolicy()

        with self.path.open("r", encoding="utf-8") as file:
            return ResourceSafetyPolicy.from_dict(json.load(file))
