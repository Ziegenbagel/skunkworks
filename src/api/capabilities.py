"""Single discovery point for every supported game capability."""

from src.api.gateways import (
    AccountGateway,
    CommunityGateway,
    GalaxyGateway,
    MannyGateway,
    MessagingGateway,
    MissionGateway,
    ProbeGateway,
    StorageGateway,
)


class GameCapabilities:
    """
    Compose domain gateways without exposing route construction elsewhere.
    """

    def __init__(self, client):
        self.account = AccountGateway(client)
        self.probes = ProbeGateway(client)
        self.storage = StorageGateway(client)
        self.mannies = MannyGateway(client)
        self.messaging = MessagingGateway(client)
        self.galaxy = GalaxyGateway(client)
        self.missions = MissionGateway(client)
        self.community = CommunityGateway(client)

    def groups(self):
        """Return stable capability group names for discovery and UI use."""

        return (
            "account",
            "probes",
            "storage",
            "mannies",
            "messaging",
            "galaxy",
            "missions",
            "community",
        )

    def recipes(self):
        return self.probes.client.request(
            "GET",
            "/api/crafting-recipes",
        )

    def reassign_mind_snapshot(self):
        return self.probes.client.request(
            "POST",
            "/api/probe/mind-snapshot/reassign",
        )
