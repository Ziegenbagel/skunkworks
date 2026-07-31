"""Player mission controls."""


class MissionGateway:
    def __init__(self, client):
        self.client = client

    def list(self):
        return self.client.request(
            "GET",
            "/api/probe/missions",
        )

    def current(self):
        return self.client.request(
            "GET",
            "/api/probe/mission",
        )

    def abandon(self, mission_id):
        return self.client.request(
            "POST",
            f"/api/probe/missions/{mission_id}/abandon",
        )
