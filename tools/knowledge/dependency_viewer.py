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

from src.utils.text import (
    humanize_name,
)
from src.knowledge.crafting import (
    CraftingKnowledge,
)

crafting = CraftingKnowledge()

recipe = crafting.get_recipe(
    "manny"
)

print("=" * 60)
print(humanize_name(recipe["name"]))
print("=" * 60)
print()

print("Description")
print("-" * 60)
print(recipe["description"])
print()

print("Dependencies")
print("-" * 60)

if recipe["crafted_components"]:

    for component, count in (
        recipe["crafted_components"].items()
    ):

        print(
            f"{humanize_name(component):<30}{count:>5}"
        )

else:

    print("None")

print()

print("Raw Resources")
print("-" * 60)

if recipe["raw_resources"]:

    for resource, amount in (
        recipe["raw_resources"].items()
    ):

        print(
            f"{humanize_name(resource):<30}{amount}"
        )

else:

    print("None")

print()

print("Effects")
print("-" * 60)

if recipe["effects"]:

    for effect, value in (
        recipe["effects"].items()
    ):

        print(
            f"{humanize_name(effect):<30}{value}"
        )

else:

    print("None")

print()

print("Build Time")
print("-" * 60)
print(
    f"{recipe['duration_seconds']} seconds"
)

print()

print("Container Space")
print("-" * 60)
print(recipe["container_space"])