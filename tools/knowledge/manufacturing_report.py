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

from src.knowledge.manufacturing_report import (
    ManufacturingReport,
)
from src.utils.text import (
    humanize_name,
)
from src.utils.time import (
    format_duration,
)
from src.knowledge.resources import (
    ResourceKnowledge,
)

report = ManufacturingReport()

resources = ResourceKnowledge()

data = report.build(
    "manny"
)

print("=" * 60)
print("Manufacturing Report")
print("=" * 60)
print()

print(
    f"Item: {humanize_name(data['recipe']['name'])}"
)

print()

print("Description")
print("-" * 60)

print(
    data["recipe"][
        "description"
    ]
)

print()

print(
    f"Build Time: "
    f"{format_duration(
        data['recipe'][
            'duration_seconds'
        ]
    )}"
)

print(
    f"Container Space: "
    f"{data['recipe']['container_space']}"
)

print()

print("Immediate Components")
print("-" * 60)

for component, count in (
    data["dependencies"].items()
):

    print(
        f"{humanize_name(component):<30}"
        f"{count}"
    )

print()

print()

print("Dependency Tree")
print("-" * 60)

tree = data[
    "dependency_tree"
]


def print_tree(
    node,
    indent="",
):

    count = node.get(
        "count",
        1,
    )

    print(
        f"{indent}"
        f"{humanize_name(node['name'])}"
        f" x{count}"
    )

    for child in node[
        "children"
    ]:

        print_tree(
            child,
            indent + "    ",
        )

print_tree(tree)

print()
print("Raw Resources")
print("-" * 60)

for resource, amount in (
    data["raw_resources"].items()
):

    print(
        f"{resources.get_display_name(resource):<30}"
        f"{amount:>8.2f}"
    )