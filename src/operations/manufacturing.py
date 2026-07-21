from src.knowledge.manufacturing_report import (
    ManufacturingReport,
)


class ManufacturingService:
    """
    Provides operational manufacturing
    queries.
    """

    def __init__(
        self,
        world,
    ):

        self.world = world

        self.report = (
            ManufacturingReport()
        )

    def build_report(
        self,
        item_name,
    ):
        """
        Return a manufacturing report for an
        item.
        """

        return self.report.build(
            item_name
        )
    
    def can_build(
        self,
        item_name,
    ):
        """
        Determine whether the required raw
        resources are currently available.
        """

        report = self.build_report(
            item_name
        )

        if report is None:

            return False

        return True
    
    def raw_resources(
        self,
        item_name,
    ):
        """
        Return the total raw resources required
        to manufacture an item.
        """

        report = self.build_report(
            item_name
        )

        if report is None:

            return None

        return report[
            "raw_resources"
        ]