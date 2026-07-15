import json
import sys
from pathlib import Path

from src.api.client import GameClient
from src.ui.dashboard import Dashboard

APP_NAME = "Skunkworks"
APP_VERSION = "0.3.0"
DIVIDER = "=" * 40

SNAPSHOT_DIRECTORY = Path("data/snapshots")


def get_requested_probe_id(probe_data):
    """Use the default probe unless --probe-id <id> was supplied."""

    default_probe_id = probe_data["defaultProbeId"]
    arguments = sys.argv[1:]

    if not arguments:
        return default_probe_id

    if len(arguments) == 2 and arguments[0] == "--probe-id":
        return int(arguments[1])

    print("Usage:")
    print("python main.py")
    print("python main.py --probe-id <probe id>")
    raise SystemExit(2)


def find_probe(probes, probe_id):
    """Find one probe summary by ID."""

    for probe in probes:
        if probe["id"] == probe_id:
            return probe

    raise ValueError(f"Probe ID {probe_id} was not found in /api/probes.")


def main():
    print(DIVIDER)
    print(APP_NAME)
    print(f"Version {APP_VERSION}")
    print(DIVIDER)
    print()

    client = GameClient()

    print("Requesting player...")
    player = client.get_player()

    print("Requesting probe list...")
    probe_data = client.get_probes()
    probes = probe_data["probes"]

    print()
    print("Available Probes")
    print("-" * 40)

    for probe in probes:
        default_marker = " (default)" if probe["isDefault"] else ""
        print(
            f"ID {probe['id']}: {probe['name']} "
            f"[{probe['status']}]{default_marker}"
        )

    probe_id = get_requested_probe_id(probe_data)
    probe = find_probe(probes, probe_id)

    print()
    print(f"Requesting sector for: {probe['name']} (ID {probe_id})")
    sector = client.get_sector(probe_id)

    SNAPSHOT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    snapshot_path = SNAPSHOT_DIRECTORY / f"sector_probe_{probe_id}.json"

    with snapshot_path.open("w", encoding="utf-8") as file:
        json.dump(sector, file, indent=4)

    print(f"Sector snapshot saved: {snapshot_path}")

    dashboard = Dashboard()
    dashboard.display(player)


if __name__ == "__main__":
    main()