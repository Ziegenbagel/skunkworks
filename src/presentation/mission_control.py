"""Stable UI view model assembled only from application services."""

from dataclasses import asdict


class MissionControlViewModelBuilder:
    """Keep future widgets isolated from the World Model and API payloads."""

    def __init__(self, operations, data_engine=None):
        self.operations = operations
        self.data_engine = data_engine

    def build(self):
        world = self.operations.world
        probe = world.probe
        fleet = getattr(world, "fleet", None) or {
            "total": 1, "idle": int(probe.get("status") == "idle"),
            "probes": (probe,),
        }
        health = self.operations.health.assess()
        return {
            "connection": self._connection_state(probe, world.snapshot),
            "focus": {
                "probeId": probe["id"],
                "name": probe.get("name", world.snapshot.get("probe", f"Probe {probe['id']}")),
                "model": probe.get("model", "generic"),
                "status": probe["status"],
            },
            "fleet": {
                "total": fleet.get("total", len(fleet.get("probes", ()))),
                "idle": fleet.get("idle", 0),
                "probes": tuple(fleet.get("probes", ())),
            },
            "probe": {
                "fuelPercent": self.operations.travel.fuel_percentage(),
                "inventoryFree": self.operations.inventory.free_capacity(),
                "mannyTotal": self.operations.mannies.total(),
                "mannyAvailable": len(self.operations.mannies.available()),
            },
            "depots": tuple(asdict(depot) for depot in self.operations.depots.all()),
            "health": asdict(health),
            "events": self.operations.events.timeline(probe["id"])
                if self.operations.events else (),
            "operations": self._operation_records(),
            "actions": self._action_records(),
            "archive": self._archive_records(),
        }

    @staticmethod
    def _connection_state(probe, snapshot):
        if not probe.get("telemetry_available", False):
            return "limited_telemetry"
        if not snapshot:
            return "disconnected"
        if not snapshot.get("fresh", False):
            return "stale"
        return "connected"

    def _operation_records(self):
        if not self.data_engine:
            return ()
        return tuple(dict(row) for row in self.data_engine.operation_records())

    def _action_records(self):
        if not self.data_engine:
            return ()
        return tuple(dict(row) for row in self.data_engine.action_history())

    def _archive_records(self):
        if not self.data_engine:
            return ()
        return tuple(dict(row) for row in self.data_engine.archive_reports())
