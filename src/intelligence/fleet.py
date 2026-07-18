class FleetAnalyzer:
    """
    Extract fleet intelligence from probe data.
    """

    def get_fleet(
        self,
        probe_data,
    ):

        probes = probe_data["probes"]

        fleet = {
            "total": len(probes),
            "default_probe": probe_data[
                "defaultProbeId"
            ],
            "idle": 0,
            "active": 0,

            "status_counts": {},

            "probes": probes,
        }

        for probe in probes:

            status = probe["status"]

            fleet["status_counts"][status] = (
                fleet["status_counts"].get(
                    status,
                    0,
                )
                + 1
            )
            if status == "idle":

                fleet["idle"] += 1

            else:

                fleet["active"] += 1

        return fleet