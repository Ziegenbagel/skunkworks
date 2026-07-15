import json


with open("data/snapshots/sector_snapshot.json", "r") as file:
    data = json.load(file)

sector = data["sector"]

print("=" * 60)
print("SECTOR EXPLORER")
print("=" * 60)

print()
print("Knowledge Level:", sector["knowledgeLevel"])
print("Confidence:", sector["confidence"])

objects = sector["objects"]

print()
print(f"Objects Found: {len(objects)}")
print()

for index, obj in enumerate(objects, start=1):
    print("-" * 60)
    print(f"Object {index}")

    print("Type :", obj.get("type"))
    print("Name :", obj.get("name"))

    if obj.get("summary"):
        print("Summary :", obj["summary"])

    print()

    print("Keys:")
    for key in obj.keys():
        print("  •", key)

print()
print("=" * 60)