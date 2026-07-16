from src.config import APP_NAME, APP_VERSION

DIVIDER = "=" * 48
SECTION = "-" * 48


class Dashboard:

    def display(
        self,
        player,
        probe_data,
        sector_resources,
):

        print(DIVIDER)
        print(f"{APP_NAME:^48}")
        print(f"Version {APP_VERSION:^38}")
        print(DIVIDER)
        print()

        self.player_section(player)
        self.fleet_section(probe_data)
        self.resources_section(
            sector_resources,
        )

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
        probe_data,
    ):

        print("Fleet")
        print(SECTION)

        probes = probe_data["probes"]

        print(f"Total Probes: {len(probes)}")
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

    def resources_section(
        self,
        sector_resources,
    ):

        print("Resources")
        print(SECTION)

        if not sector_resources:

            print("No mineable resources detected.")
            print()

            return

        for asteroid in sector_resources:

            resources = asteroid["resources"]

            if resources.get("metals", 0) > 0:

                title = "Metal Asteroid"

            elif (
                resources.get("ice", 0) > 0
                or resources.get(
                    "carbon_compounds",
                    0,
                )
                > 0
            ):

                title = "Ice / Organic Asteroid"

            else:

                title = "Unknown Asteroid"

            print(title)

            print()

            print("Remaining")

            for resource, amount in resources.items():

                if amount <= 0:
                    continue

                label = resource.replace(
                    "_",
                    " ",
                ).title()

                print(
                    f"  {label:<20}{amount:>10.2f}"
                )

            print()

            print("Composition")

            for (
                resource,
                amount,
            ) in asteroid[
                "composition"
            ].items():

                if amount <= 0:
                    continue

                label = resource.replace(
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