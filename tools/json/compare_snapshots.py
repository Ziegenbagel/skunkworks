import json
import sys
from collections import Counter
from pathlib import Path

APP_NAME = "Snapshot Compare"
APP_VERSION = "0.1.0"

TOOLKIT_NAME = "Skunkworks Laboratory"
TOOLKIT_SUBTITLE = "Developer Toolkit"

DIVIDER = "=" * 60


def load_snapshot(path):
    """Load a snapshot from disk."""

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def count_types(objects):
    """Count objects by their 'type' field."""

    counts = Counter()

    for obj in objects:
        counts[obj.get("type", "unknown")] += 1

    return counts


def print_section(title):
    print()
    print(DIVIDER)
    print(title)
    print(DIVIDER)


def compare_counter(title, counter_a, counter_b):

    print_section(title)

    all_types = sorted(set(counter_a.keys()) | set(counter_b.keys()))

    differences = 0

    for object_type in all_types:

        before = counter_a.get(object_type, 0)
        after = counter_b.get(object_type, 0)

        marker = " " if before == after else "*"

        if before != after:
            differences += 1

        print(
            f"{marker} {object_type:<24}"
            f"A: {before:<4}"
            f"B: {after:<4}"
        )

    return differences


def main():

    print(DIVIDER)
    print(TOOLKIT_NAME)
    print(TOOLKIT_SUBTITLE)
    print("-" * 60)
    print(f"Tool: {APP_NAME}")
    print(f"Version: {APP_VERSION}")
    print(DIVIDER)
    print()

    if len(sys.argv) != 3:
        print("Usage:")
        print(
            "python tools/json/compare_snapshots.py "
            "<snapshot A> <snapshot B>"
        )
        return

    path_a = Path(sys.argv[1])
    path_b = Path(sys.argv[2])

    if not path_a.exists():
        print(f"Missing: {path_a}")
        return

    if not path_b.exists():
        print(f"Missing: {path_b}")
        return

    print(f"Loading {path_a.name}")
    snapshot_a = load_snapshot(path_a)

    print(f"Loading {path_b.name}")
    snapshot_b = load_snapshot(path_b)

    print()

    sector_objects_a = snapshot_a["sector"]["objects"]
    sector_objects_b = snapshot_b["sector"]["objects"]

    inventory_items_a = snapshot_a["inventory"]["items"]
    inventory_items_b = snapshot_b["inventory"]["items"]

    resource_stocks_a = snapshot_a["inventory"]["resourceStocks"]
    resource_stocks_b = snapshot_b["inventory"]["resourceStocks"]

    containers_a = snapshot_a["inventory"]["containers"]
    containers_b = snapshot_b["inventory"]["containers"]

    total_differences = 0

    total_differences += compare_counter(
        "Sector Objects",
        count_types(sector_objects_a),
        count_types(sector_objects_b),
    )

    total_differences += compare_counter(
        "Inventory Items",
        count_types(inventory_items_a),
        count_types(inventory_items_b),
    )

    print_section("Inventory Totals")

    inventory_values = [
        ("Containers", len(containers_a), len(containers_b)),
        ("Resource Stocks", len(resource_stocks_a), len(resource_stocks_b)),
    ]

    for label, before, after in inventory_values:

        marker = " " if before == after else "*"

        if before != after:
            total_differences += 1

        print(
            f"{marker} {label:<24}"
            f"A: {before:<4}"
            f"B: {after:<4}"
        )

    print_section("Summary")

    print(f"Differences Found: {total_differences}")

    if total_differences == 0:
        print("Snapshots are structurally identical.")
    else:
        print("* indicates a detected difference.")


if __name__ == "__main__":
    main()