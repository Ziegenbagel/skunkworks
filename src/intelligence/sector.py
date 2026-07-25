"""
SectorAnalyzer

Builds a normalized representation of the currently
observed sector from the /api/probe/{probeId}/sector
endpoint.
"""

from src.intelligence.resources import (
    ResourceAnalyzer,
)


class SectorAnalyzer:
    """
    Produces the application's normalized sector model.
    """

    def __init__(self):

        self.resource_analyzer = (
            ResourceAnalyzer()
        )

    def analyze(self, snapshot):

        return {
            "resources": (
                self.resource_analyzer.get_sector_resources(
                    snapshot
                )
            ),
            "snapshot": snapshot,
        }