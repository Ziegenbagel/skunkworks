import json
import sys
from collections import Counter
from pathlib import Path

APP_NAME = "JSON Tree Explorer"
APP_VERSION = "0.3.1"

TOOLKIT_NAME = "Skunkworks Laboratory"
TOOLKIT_SUBTITLE = "Developer Toolkit"

DIVIDER = "=" * 60
SECTION_DIVIDER = "-" * 60
INDENT_SIZE = 4


def load_json(file_path: Path):
    """Load and parse a JSON file from disk."""

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def indentation(level: int) -> str:
    """Return indentation for a tree level."""

    return " " * (level * INDENT_SIZE)


def object_label(item: dict) -> str:
    """
    Return the most useful label for a dictionary in a JSON list.

    Game API objects usually identify themselves with type, kind, or name.
    """

    return (
        item.get("type")
        or item.get("kind")
        or item.get("name")
        or "unknown"
    )


def describe_primitive_list(items: list, level: int) -> None:
    """Display a compact summary of a list containing primitive values."""

    prefix = indentation(level)
    type_counts = Counter(type(item).__name__ for item in items)

    print(f"{prefix}Contains:")

    for value_type, count in sorted(type_counts.items()):
        print(f"{prefix}{' ' * INDENT_SIZE}{value_type:<24} x{count}")


def describe_object_list(items: list[dict], level: int) -> None:
    """Display a compact summary of a list containing dictionaries."""

    prefix = indentation(level)
    labels = Counter(object_label(item) for item in items)

    print(f"{prefix}Contains:")

    for label, count in sorted(labels.items()):
        print(f"{prefix}{' ' * INDENT_SIZE}{str(label):<24} x{count}")


def describe_list(items: list, level: int) -> None:
    """
    Summarize a JSON list and show one representative item structure.

    The representative structure keeps output readable while the summary shows
    whether the list contains multiple API object types.
    """

    prefix = indentation(level)

    if not items:
        print(f"{prefix}<empty list>")
        return

    if all(isinstance(item, dict) for item in items):
        describe_object_list(items, level)
        print()
        print(f"{prefix}Representative structure:")
        print_tree(items[0], level + 1)
        return

    if all(not isinstance(item, (dict, list)) for item in items):
        describe_primitive_list(items, level)
        return

    print(f"{prefix}Contains mixed item types:")

    type_counts = Counter(type(item).__name__ for item in items)

    for item_type, count in sorted(type_counts.items()):
        print(f"{prefix}{' ' * INDENT_SIZE}{item_type:<24} x{count}")

    representative = items[0]

    if isinstance(representative, (dict, list)):
        print()
        print(f"{prefix}Representative structure:")
        print_tree(representative, level + 1)


def print_tree(data, level: int = 0) -> None:
    """
    Recursively print JSON structure without displaying raw values.

    This function is intentionally separate from loading and list analysis so
    future versions can add path exploration without changing core behavior.
    """

    prefix = indentation(level)

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{prefix}{key} (dict)")
                print_tree(value, level + 1)

            elif isinstance(value, list):
                print(f"{prefix}{key} (list: {len(value)})")
                describe_list(value, level + 1)

            else:
                print(f"{prefix}{key} ({type(value).__name__})")

        return

    if isinstance(data, list):
        print(f"{prefix}<root list: {len(data)}>")
        describe_list(data, level + 1)
        return

    print(f"{prefix}{type(data).__name__}")


def print_banner() -> None:
    """Print the standard Skunkworks Laboratory tool header."""

    print(DIVIDER)
    print(TOOLKIT_NAME)
    print(TOOLKIT_SUBTITLE)
    print(SECTION_DIVIDER)
    print(f"Tool: {APP_NAME}")
    print(f"Version: {APP_VERSION}")
    print(DIVIDER)
    print()
    print("Purpose:")
    print("Explore the structure of JSON snapshots without displaying values.")
    print()


def main() -> None:
    """Load a JSON file provided on the command line and print its structure."""

    print_banner()

    if len(sys.argv) != 2:
        print("Usage:")
        print("uv run tools/json/json_tree.py <json file>")
        return

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    if not file_path.is_file():
        print(f"Not a file: {file_path}")
        return

    try:
        print(f"Loading JSON: {file_path}")
        data = load_json(file_path)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}")
        return
    except OSError as error:
        print(f"Could not read file: {error}")
        return

    print("✓ JSON loaded successfully")
    print()
    print(DIVIDER)
    print("JSON STRUCTURE")
    print(DIVIDER)

    print_tree(data)


if __name__ == "__main__":
    main()