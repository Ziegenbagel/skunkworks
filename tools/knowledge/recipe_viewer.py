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

from src.knowledge.crafting import (
    CraftingKnowledge,
)


crafting = CraftingKnowledge()

print("Recipes")
print("-" * 40)

for recipe in crafting.list_recipes():

    print(recipe)

print()

print(
    "Manny Exists:",
    crafting.recipe_exists(
        "manny"
    ),
)

print(
    "Probe Exists:",
    crafting.recipe_exists(
        "probe"
    ),
)