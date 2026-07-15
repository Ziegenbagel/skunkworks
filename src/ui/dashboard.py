APP_NAME = "Skunkworks"
APP_VERSION = "0.3.0"

DIVIDER = "=" * 48
SECTION = "-" * 48


class Dashboard:
    def display(self, player):
        print(DIVIDER)
        print(f"{APP_NAME:^48}")
        print(f"Version {APP_VERSION:^38}")
        print(DIVIDER)
        print()

        self.player_section(player)
        self.fleet_section()
        self.planner_section()
        self.alerts_section()

        print(DIVIDER)
        print("Ready.")
        print()

    def player_section(self, player):
        print("Player")
        print(SECTION)

        print(f"Name: {player['player']['displayName']}")
        print(f"Player ID: {player['player']['id']}")
        print("API: Connected")

        print()

    def fleet_section(self):
        print("Fleet")
        print(SECTION)
        print("Probes:")
        print("Mannys:")
        print("Containers:")
        print("Atomic Printers:")
        print("SCUT Relays:")
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