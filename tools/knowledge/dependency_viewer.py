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
from src.utils.text import (
    humanize_name,
)


def print_tree(
    node,
    indent="",
):

    print(
        f"{indent}"
        f"{humanize_name(node['name'])}"
        f" x{node.get('count', 1)}"
    )

    for child in node["children"]:

        print_tree(
            child,
            indent + "    ",
        )


crafting = CraftingKnowledge()

tree = crafting.get_dependency_tree(
    "manny"
)

print("=" * 60)
print("Manufacturing Dependency Tree")
print("=" * 60)
print()

print_tree(tree)