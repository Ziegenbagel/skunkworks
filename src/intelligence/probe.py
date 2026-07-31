"""Normalize probe telemetry at the API boundary."""


class ProbeAnalyzer:
    """Produce a stable internal probe representation."""

    def analyze(self, probe):
        limited = probe.get("status") == "out_of_scut_range"

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
            "movement": probe.get("movement"),
            "navigation": probe.get("navigation", {}),
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
