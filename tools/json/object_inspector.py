import json
import sys
from pathlib import Path


APP_NAME = "Skunkworks Laboratory"
TOOL_NAME = "Object Inspector"
VERSION = "0.1.0"

DIVIDER = "=" * 60


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def print_header():
    print(DIVIDER)
    print(APP_NAME)
    print("Developer Toolkit")
    print("-" * 60)
    print(f"Tool: {TOOL_NAME}")
    print(f"Version: {VERSION}")
    print(DIVIDER)
    print()


def inspect_objects(data):
    objects = data["sector"]["objects"]

    print(f"Objects Found: {len(objects)}")
    print()

    for index, obj in enumerate(objects, start=1):

        print("-" * 60)
        print(f"Object #{index}")
        print("-" * 60)

        print(f"Type: {obj.get('type')}")
        print(f"ID:   {obj.get('id')}")

        if obj.get("name"):
            print(f"Name: {obj['name']}")

        print()

        mineable = obj.get("mannyMineable", False)

        print(f"mannyMineable: {mineable}")

        if "resources" in obj:
            print(f"resources: {obj['resources']}")

        if "resourceTypes" in obj:
            print(f"resourceTypes: {obj['resourceTypes']}")

        if "resourceAmounts" in obj:
            print("resourceAmounts:")

            for key, value in obj["resourceAmounts"].items():
                print(f"  {key}: {value}")

        if "resourceComposition" in obj:
            print("resourceComposition:")

            for key, value in obj["resourceComposition"].items():
                print(f"  {key}: {value}")

        print()

        if "minableTargets" in obj:
            print(
                f"Contains {len(obj['minableTargets'])} minableTargets"
            )

        print()


def main():

    if len(sys.argv) != 2:
        print("Usage:")
        print("uv run tools/json/object_inspector.py <snapshot.json>")
        sys.exit(1)

    path = Path(sys.argv[1])

    print_header()

    print(f"Loading: {path}")
    print()

    data = load_json(path)

    inspect_objects(data)


if __name__ == "__main__":
    main()