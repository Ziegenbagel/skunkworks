from src.config import APP_NAME, APP_VERSION

DIVIDER = "=" * 48
SECTION = "-" * 48


class Dashboard:

    def display(
        self,
        world,
    ):

        print(DIVIDER)
        print(f"{APP_NAME:^48}")
        print(f"Version {APP_VERSION:^38}")
        print(DIVIDER)
        print()

        self.player_section(world.player)
        self.fleet_section(world.fleet)
        self.snapshot_section(world.snapshot)
        self.inventory_section(world.inventory)
        self.resources_section(world.resources)
        self.planner_section()
        self.alerts_section()

        print(DIVIDER)
        print("Ready.")
        print()

    def player_section(self, player):

        print("Player")
        print(SECTION)

        print(
            f"Name: {player['player']['displayName']}"
        )

        print(
            f"Player ID: {player['player']['id']}"
        )

        print("API: Connected")

        print()

    def fleet_section(
        self,
        fleet,
    ):

        print("Fleet")
        print(SECTION)

        probes = fleet["probes"]

        print(
            f"Total Probes: {fleet['total']}"
        )
        print()

        print("Operational")
        print()

        print(
            f"  Available   {fleet['idle']}"
        )

        print(
            f"  Busy        {fleet['active']}"
        )

        print()

        print("Status Summary")
        print()

        status_counts = fleet["status_counts"]

        for status, count in status_counts.items():

            print(
                f"  {status.title():<12}{count}"
            )

        print()

        print("Probe Details")
        print()

        for probe in probes:

            default = (
                " (Default)"
                if probe["isDefault"]
                else ""
            )

            print(
                f"{probe['name']}{default}"
            )

            print(
                f"  Status : {probe['status']}"
            )

            print()

    def snapshot_section(self, snapshot_info):
        print("Snapshot")
        print(SECTION)

        print(
            f"Current Probe: "
            f"{snapshot_info['probe']}"
        )

        print(
            f"Last Refresh: "
            f"{snapshot_info['last_refresh']}"
        )

        print(
            f"Snapshot Age: "
            f"{snapshot_info['age']}"
        )

        status = (
            "Fresh"
            if snapshot_info["fresh"]
            else "Stale"
        )

        print(f"Status: {status}")
        print()

    def inventory_section(
        self,
        inventory,
    ):

        print("Probe Inventory")
        print(SECTION)

        print(
            f"Capacity: "
            f"{inventory['capacity']:.2f}"
        )

        print(
            f"Used: "
            f"{inventory['used_capacity']:.2f}"
        )

        print(
            f"Free: "
            f"{inventory['free_capacity']:.2f}"
        )

        print()

        print("Cargo")

        for resource_name, amount in (
            inventory["resource_stocks"].items()
        ):

            label = (
                resource_name
                .replace("_", " ")
                .title()
            )

            print(
                f"  {label:<20}{amount:>10.2f}"
            )

        print()

    def resources_section(
        self,
        sector_resources,
    ):

        print("Sector Resources")
        print(SECTION)

        if not sector_resources:

            print("No mineable resources detected.")
            print()

            return

        for resource in sector_resources:

            remaining_resources = resource["resources"]

            classification = resource["classification"]

            if classification == "persistent":
                title = "Persistent Asteroid"
            else:
                title = "Wandering Resource"

            print(title)
            print()

            print("Materials")

            for resource_type in resource["resource_types"]:

                label = (
                    resource_type
                    .replace("_", " ")
                    .title()
                )

                print(f"  {label}")

            print()

            print("Remaining")

            for resource_name, amount in remaining_resources.items():

                if amount <= 0:
                    continue

                label = resource_name.replace(
                    "_",
                    " ",
                ).title()

                print(
                    f"  {label:<20}{amount:>10.2f}"
                )

            print()

            print("Composition")

            for (
                resource_name,
                amount,
            ) in resource[
                "composition"
            ].items():

                if amount <= 0:
                    continue

                label = resource_name.replace(
                    "_",
                    " ",
                ).title()

                print(
                    f"  {label:<20}{amount*100:>9.1f}%"
                )

            print()

    def planner_section(self):

        print("Planner")
        print(SECTION)

        print("Status:")
        print("Next Evaluation:")

        print()

    def alerts_section(self):

        print("Alerts")
        print(SECTION)

        print("No active alerts.")

        print()