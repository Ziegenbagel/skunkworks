from pprint import pprint

from src.api.client import GameClient

client = GameClient()

for probe_id in (644, 762):

    print("=" * 60)
    print(f"PROBE {probe_id}")
    print("=" * 60)

    probe = client.get_probe(probe_id)["probe"]
    sector = client.get_sector(probe_id)

    print("\nProbe Status")
    print("--------------------")
    print(probe["status"])

    print("\nMovement")
    print("--------------------")
    pprint(probe["movement"])

    print("\nSector")
    print("--------------------")

    pprint(
        sector.get("sector", {})
    )