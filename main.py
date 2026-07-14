from src.api.client import GameClient

APP_NAME = "Skunkworks"
APP_VERSION = "0.1.0"
DIVIDER = "=" * 40


def main():
    print(DIVIDER)
    print(APP_NAME)
    print(f"Version {APP_VERSION}")
    print(DIVIDER)
    print()

    print("1. Initializing...")
    print("2. Python Environment OK")

    print("3. Creating GameClient...")
    client = GameClient()
    print("4. GameClient Created")

    print("5. Requesting Player...")
    player = client.get_player()
    print("6. Player Received")

    print("✓ Connected to Von Neumann Game")
    print()

    print(f"Player: {player['player']['displayName']}")

    print()
    print("Ready.")


if __name__ == "__main__":
    main()