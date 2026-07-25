"""
ProbeAnalyzer

Builds a normalized representation of the currently
selected probe from the /api/probe/{probeId} endpoint.
"""


class ProbeAnalyzer:
    """
    Produces the application's normalized probe model.
    """

    def analyze(self, probe):

        return {
            "id": probe["id"],
            "name": probe["name"],
            "status": probe["status"],
            "sensor_mode": probe["sensorMode"],
            "fuel": probe["fuel"],
            "movement": probe["movement"],
            "navigation": probe["navigation"],
            "systems": probe["systems"],
            "inventory": probe["inventory"],
        }