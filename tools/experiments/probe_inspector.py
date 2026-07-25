from pprint import pprint

from src.api.client import GameClient

client = GameClient()

probe_data = client.get_probes()
probe_id = probe_data["defaultProbeId"]

probe = client.get_probe(probe_id)["probe"]

print("=" * 60)
print("PROBE INSPECTOR")
print("=" * 60)
print()

while True:

    print("Available sections:")

    for key in probe:
        print(f" - {key}")

    print()

    section = input(
        "Section (blank to quit): "
    ).strip()

    if not section:
        break

    if section not in probe:
        print("Unknown section.\n")
        continue

    print()
    print("=" * 60)
    print(section.upper())
    print("=" * 60)

    pprint(
        probe[section],
        sort_dicts=False,
        width=100,
    )

    print()