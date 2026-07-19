from pathlib import Path
import sys

project_root = (
    Path(__file__)
    .resolve()
    .parents[2]
)

sys.path.insert(
    0,
    str(project_root),
)

from src.knowledge.gameplay import (
    GameplayKnowledge,
)

knowledge = GameplayKnowledge()

print("=" * 60)
print("Gameplay Knowledge Summary")
print("=" * 60)
print()

print("Top-Level Sections")
print("-" * 60)

for key, value in knowledge.data.items():

    value_type = type(value).__name__

    if hasattr(value, "__len__"):
        size = len(value)
    else:
        size = "-"

    print(
        f"{key:<24}"
        f"{value_type:<12}"
        f"{size}"
    )

    if isinstance(value, dict):

        for child_key in value.keys():

            print(
                f"    - {child_key}"
            )

    print()

print("=" * 60)
print("Crafting Schema Audit")
print("=" * 60)
print()

all_fields = set()

for item_name, recipe in (
    knowledge.data["crafting"].items()
):

    print(item_name)

    for field in recipe:

        all_fields.add(field)

        print(f"    - {field}")

    print()

print("=" * 60)
print("Unique Fields")
print("=" * 60)
print()

for field in sorted(all_fields):

    print(field)