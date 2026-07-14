from src.api import client
import json
from src.api.client import GameClient
from src.ui.dashboard import Dashboard

APP_NAME = "Skunkworks"
APP_VERSION = "0.2.0"
DIVIDER = "=" * 40


def main():
    print(DIVIDER)
    print(APP_NAME)
    print(f"Version {APP_VERSION}")
    print(DIVIDER)
    print()

    print("1. Initializing...")
    print("2. Python Environment OK")

    print("3. Creating GameClient...")
    client = GameClient()
    print("4. GameClient Created")

    print("5. Requesting Player...")
    player = client.get_player()

    print("6. Requesting Sector...")
    sector = client.get_sector()

    print("Sector endpoint reached.")
    print(type(sector))
    print(sector.keys())

    with open("sector_snapshot.json", "w") as file:
        json.dump(sector, file, indent=4)

    print("Sector snapshot saved.")

    dashboard = Dashboard()
    dashboard.display(player)

if __name__ == "__main__":
    main()