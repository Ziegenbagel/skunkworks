"""Sector observations and fleet-wide exploration history."""


class GalaxyGateway:
    def __init__(self, client):
        self.client = client

    def observe_sector(self, x, y, z):
        return self.client.request(
            "GET",
            "/api/sector",
            params={"x": x, "y": y, "z": z},
        )

    def visited_sectors(self):
        return self.client.request(
            "GET",
            "/api/visited-sectors",
        )
