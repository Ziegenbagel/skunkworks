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
        Determine whether an item can be
        manufactured using the currently
        available raw resources.
        """

        missing = self.missing_resources(
            item_name
        )

        if missing is None:

            return False

        return len(
            missing
        ) == 0
    
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
    
    def missing_resources(
        self,
        item_name,
    ):
        """
        Return any raw resources still needed
        to manufacture an item.
        """

        report = self.build_report(
            item_name
        )

        if report is None:

            return None

        inventory = self.world.inventory[
            "resource_stocks"
        ]

        missing = {}

        for resource, required in (
            report[
                "raw_resources"
            ].items()
        ):

            available = inventory.get(
                resource,
                0,
            )

            if available < required:

                missing[resource] = round(
                    required - available,
                    2,
                )

        return missing