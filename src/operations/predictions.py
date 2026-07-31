"""Transparent local forecasts between authoritative API refreshes."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class Prediction:
    metric: str
    value: float | datetime
    confidence: float
    basis: str
    observed_at: datetime
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class PredictionDrift:
    metric: str
    predicted: float
    observed: float
    absolute_error: float
    relative_error: float


class PredictionService:
    def __init__(self, operations, now=None):
        self.operations = operations
        self._now = now or (lambda: datetime.now(UTC))

    def task_completions(self):
        predictions = []
        now = self._now()
        for manny in self.operations.mannies.all():
            task = manny.get("currentTask") or {}
            raw = task.get("endsAt") if isinstance(task, dict) else None
            if raw:
                try:
                    ends = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except (TypeError, ValueError):
                    continue
                predictions.append(
                    Prediction(
                        f"manny:{manny['id']}:completion", ends, 0.95,
                        "authoritative task end time", now,
                    )
                )
        return tuple(predictions)

    def resource_exhaustion(self, resource_type, remaining, rate_per_hour):
        now = self._now()
        if rate_per_hour <= 0:
            return None
        hours = max(0.0, remaining) / rate_per_hour
        return Prediction(
            f"resource:{resource_type}:exhaustion",
            now + timedelta(hours=hours), 0.65,
            "current remaining amount / observed mining rate", now,
            ("mining rate remains constant",),
        )

    def inventory_saturation(self, free_capacity, rate_per_hour):
        now = self._now()
        if rate_per_hour <= 0:
            return None
        return Prediction(
            "inventory:saturation",
            now + timedelta(hours=max(0.0, free_capacity) / rate_per_hour),
            0.65, "free capacity / observed inflow rate", now,
            ("inflow remains constant",),
        )

    def production_completion(self, remaining_units, seconds_per_unit):
        now = self._now()
        return Prediction(
            "production:completion",
            now + timedelta(seconds=max(0, remaining_units) * max(0, seconds_per_unit)),
            0.75, "remaining units × current recipe duration", now,
            ("workers and input supply remain available",),
        )

    def transport_throughput(self, amount_per_trip, cycle_minutes):
        now = self._now()
        value = amount_per_trip * 60 / cycle_minutes if cycle_minutes > 0 else 0
        return Prediction(
            "transport:throughput_per_hour", value, 0.6,
            "cargo per trip / observed cycle duration", now,
            ("route and loading time remain stable",),
        )

    def fuel_after_route(self, current_fuel, hops, fuel_per_hop):
        now = self._now()
        return Prediction(
            "probe:fuel_after_route",
            max(0.0, current_fuel - max(0, hops) * max(0, fuel_per_hop)),
            0.9, "current fuel - planned hop cost", now,
            ("route does not change",),
        )

    def integrity_at_arrival(self, current_integrity, damage_per_hop, hops):
        now = self._now()
        return Prediction(
            "probe:integrity_at_arrival",
            max(0.0, current_integrity - max(0, damage_per_hop) * max(0, hops)),
            0.55, "current integrity - observed damage trend", now,
            ("future sectors match the observed damage rate",),
        )

    def fleet_metrics(self):
        now = self._now()
        total = max(1, self.operations.mannies.total())
        busy = total - len(self.operations.mannies.idle())
        fuel = self.operations.travel.fuel_percentage()
        inventory = self.operations.world.probe.get("inventory", {})
        integrity = self._integrity()
        return (
            Prediction("manny:utilization_percent", busy / total * 100, 1.0,
                       "current authoritative Manny task state", now),
            Prediction("probe:fuel_percent", fuel, 1.0,
                       "current authoritative fuel state", now),
            Prediction("inventory:free_capacity", inventory.get("freeCapacity", 0), 1.0,
                       "current authoritative inventory state", now),
            Prediction("probe:integrity_percent", integrity, 0.9,
                       "current probe systems", now),
        )

    @staticmethod
    def drift(prediction, observed):
        predicted = float(prediction.value)
        error = abs(predicted - observed)
        return PredictionDrift(
            prediction.metric, predicted, observed, error,
            error / max(abs(observed), 1e-9),
        )

    def _integrity(self):
        systems = self.operations.world.probe.get("systems", {})
        values = []
        for system in systems.values():
            if isinstance(system, dict):
                value = system.get("integrity", system.get("health"))
                if isinstance(value, (int, float)):
                    values.append(value)
        return min(values) if values else 100
