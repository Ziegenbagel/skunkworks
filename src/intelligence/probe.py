"""Normalize probe telemetry at the API boundary."""


class ProbeAnalyzer:
    """Produce a stable internal probe representation."""

    def analyze(self, probe):
        limited = probe.get("status") == "out_of_scut_range"
        navigation = probe.get("navigation") or {}
        movement = (
            probe.get("movement")
            or probe.get("travel")
            or navigation.get("movement")
            or navigation.get("travel")
            or {}
        )
        movement = dict(movement)
        for stable_key, aliases in {
            "velocity": ("velocity", "velocityC", "speedC"),
            "heading": ("heading", "vector", "direction", "headingVector"),
        }.items():
            if movement.get(stable_key) not in (None, "", {}):
                continue
            for source in (probe, navigation):
                value = next((source.get(key) for key in aliases if source.get(key) not in (None, "", {})), None)
                if value is not None:
                    movement[stable_key] = value
                    break

        return {
            "id": probe["id"],
            "name": probe["name"],
            "model": probe.get("model", "generic"),
            "status": probe["status"],
            "telemetry_available": not limited,
            "sector": probe.get("sector"),
            "sensor_mode": probe.get("sensorMode"),
            "fuel": probe.get(
                "fuel",
                {
                    "deuterium": 0,
                    "maxDeuterium": 0,
                },
            ),
            "movement": movement,
            "velocity": movement.get("velocity"),
            "heading": movement.get("heading"),
            "navigation": navigation,
            "systems": probe.get("systems", {}),
            "inventory": probe.get(
                "inventory",
                {
                    "capacity": 0,
                    "usedCapacity": 0,
                    "freeCapacity": 0,
                    "items": [],
                    "resourceStocks": [],
                    "containers": [],
                    "externalTanks": [],
                },
            ),
        }
