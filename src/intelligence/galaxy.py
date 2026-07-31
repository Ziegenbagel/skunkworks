"""Construct the map model from public exploration history."""

from src.models.galaxy import GalaxyMap


class GalaxyMapBuilder:
    """Merge fleet-wide and per-probe visit histories."""

    def build(
        self,
        fleet_history,
        probe_histories=None,
    ):
        galaxy = GalaxyMap()

        for visit in fleet_history.get(
            "visitedSectors",
            [],
        ):
            galaxy.record_visit(visit)

        for probe_id, history in (
            probe_histories or {}
        ).items():
            for visit in history.get(
                "visitedSectors",
                [],
            ):
                galaxy.record_visit(
                    visit,
                    probe_id=probe_id,
                )

        return galaxy
