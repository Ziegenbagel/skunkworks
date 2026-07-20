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
from src.knowledge.resources import (
    get_display_name,
)
from src.utils.text import (
    humanize_name,
)


crafting = CraftingKnowledge()

item = "manny"

totals = crafting.get_total_raw_resources(
    item
)

print("=" * 60)
print("Raw Resource Requirements")
print("=" * 60)
print()

print(
    f"Item: {humanize_name(item)}"
)

print()

print("Resources")
print("-" * 60)

for resource, amount in (
    totals.items()
):

    print(
        f"{get_display_name(resource):<25}"
        f"{amount:>10.2f}"
    )