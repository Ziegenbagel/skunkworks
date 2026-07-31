"""Fleet readiness, bottleneck, and stale-data assessment."""

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthFinding:
    code: str
    severity: str
    summary: str
    entity_id: str | int | None = None


@dataclass(frozen=True)
class OperationalHealth:
    state: str
    readiness_percent: float
    findings: tuple[HealthFinding, ...]


class OperationalHealthService:
    def __init__(self, operations):
        self.operations = operations

    def assess(self):
        findings = []
        probe = self.operations.world.probe
        snapshot = self.operations.world.snapshot or {}
        if not probe.get("telemetry_available", False):
            findings.append(HealthFinding(
                "limited_telemetry", "critical", "Probe telemetry is unavailable.",
                probe.get("id"),
            ))
        elif not snapshot.get("fresh", False):
            findings.append(HealthFinding(
                "stale_snapshot", "warning", "Probe snapshot is stale.", probe.get("id"),
            ))
        if self.operations.travel.fuel_percentage() <= 20:
            findings.append(HealthFinding(
                "low_fuel", "warning", "Deuterium reserve is at or below 20%.",
                probe.get("id"),
            ))
        inventory = probe.get("inventory", {})
        capacity = inventory.get("capacity", 0)
        free = inventory.get("freeCapacity", 0)
        if capacity and free / capacity <= 0.1:
            findings.append(HealthFinding(
                "inventory_saturation", "warning", "Inventory has 10% or less free capacity.",
                probe.get("id"),
            ))
        if self.operations.mannies.total() and not self.operations.mannies.available():
            findings.append(HealthFinding(
                "no_available_mannies", "notice", "No Manny can accept a new order.",
                probe.get("id"),
            ))
        for depot in self.operations.depots.all():
            if depot.needs_transport:
                findings.append(HealthFinding(
                    "depot_transport_needed", "warning",
                    f"{depot.name} storage requires collection.", depot.asteroid_id,
                ))
        penalty = {"notice": 5, "warning": 15, "critical": 40}
        readiness = max(0.0, 100 - sum(penalty[item.severity] for item in findings))
        state = "critical" if any(item.severity == "critical" for item in findings) \
            else "degraded" if findings else "ready"
        return OperationalHealth(state, readiness, tuple(findings))
