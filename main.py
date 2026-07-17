import sys

from src.intelligence.inventory import InventoryAnalyzer
from src.intelligence.snapshot import SnapshotAnalyzer
from src.intelligence.resources import ResourceAnalyzer
from src.api.client import GameClient
from src.snapshot.manager import SnapshotManager
from src.ui.dashboard import Dashboard

from src.config import APP_NAME, APP_VERSION

DIVIDER = "=" * 40


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

    raise ValueError(
        f"Probe ID {probe_id} was not found."
    )


def main():

    print("Starting Skunkworks...")
    print()

    client = GameClient()

    snapshot_manager = SnapshotManager(client)

    resource_analyzer = ResourceAnalyzer()

    print("Requesting player...")
    player = client.get_player()

    print("Requesting probe list...")
    probe_data = client.get_probes()
    probes = probe_data["probes"]

    print()
    print("Available Probes")
    print("-" * 40)

    for probe in probes:

        default_marker = (
            " (default)"
            if probe["isDefault"]
            else ""
        )

        print(
            f"ID {probe['id']}: "
            f"{probe['name']} "
            f"[{probe['status']}]"
            f"{default_marker}"
        )

    probe_id = get_requested_probe_id(probe_data)
    probe = find_probe(probes, probe_id)

    print()
    print(
        f"Refreshing snapshot for "
        f"{probe['name']}..."
    )

    sector, snapshot_path = (
        snapshot_manager.refresh_sector(probe_id)
    )

    print(f"Snapshot updated: {snapshot_path}")

    sector_resources = (
        resource_analyzer.get_sector_resources(
            sector
        )
    )

    snapshot_analyzer = SnapshotAnalyzer(snapshot_path)

    snapshot_info = snapshot_analyzer.get_snapshot_info(
        probe["name"]
    )

    inventory_analyzer = InventoryAnalyzer()

    inventory_info = (
        inventory_analyzer.get_inventory(
            sector
        )
    )

    dashboard = Dashboard()

    dashboard.display(
        player,
        probe_data,
        sector_resources,
        snapshot_info,
        inventory_info,
)


if __name__ == "__main__":
    main()