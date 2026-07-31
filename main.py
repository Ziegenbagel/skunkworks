from src.intelligence.world_builder import WorldBuilder
from src.api.client import GameClient
from src.snapshot.manager import SnapshotManager
from src.ui.dashboard import Dashboard
from src.planner import Planner
from src.recipes.manager import RecipeManager
from src.operations.operations import (
    Operations,
)

from src.config import APP_NAME, APP_VERSION
from src.application.probe_selector import (
    ProbeSelectionError,
    ProbeSelector,
)

DIVIDER = "=" * 40


def main():

    print("Starting Skunkworks...")
    print()

    client = GameClient()
    api_version = client.ensure_compatible_api()

    print(f"Von Neumann Game API v{api_version}")

    snapshot_manager = SnapshotManager(client)

    recipe_manager = RecipeManager()

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

    try:
        probe = ProbeSelector().select(probe_data)
    except ProbeSelectionError as error:
        print(error)
        raise SystemExit(2) from error

    probe_id = probe["id"]

    builder = WorldBuilder()

    probe_details = client.get_probe(probe_id)

    if probe.get("isReachable", True):
        mannies = client.get_mannies(probe_id)

        print()
        print(
            f"Refreshing snapshot for "
            f"{probe['name']}..."
        )

        snapshot, snapshot_path = (
            snapshot_manager.refresh_sector(probe_id)
        )

        print(f"Snapshot updated: {snapshot_path}")

        world = builder.build(
            player=player,
            probe_data=probe_data,
            probe=probe_details["probe"],
            snapshot=snapshot,
            snapshot_path=snapshot_path,
            probe_name=probe["name"],
            mannies=mannies,
        )
    else:
        print()
        print(
            "Selected probe is outside SCUT range; "
            "showing limited telemetry."
        )
        world = builder.build_limited(
            player=player,
            probe_data=probe_data,
            probe=probe_details["probe"],
            probe_name=probe["name"],
        )

    recipes = client.get_crafting_recipes()
    recipe_manager.load(recipes)

    operations = Operations(
        world,
        recipe_manager,
    )

    planner = Planner(operations)
    tasks = planner.tasks()
    

    dashboard = Dashboard()

    dashboard.display(
        world,
        tasks,
    )


if __name__ == "__main__":
    main()
