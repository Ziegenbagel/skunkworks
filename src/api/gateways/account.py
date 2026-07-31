"""Authenticated player and API-key controls."""


class AccountGateway:
    def __init__(self, client):
        self.client = client

    def player(self):
        return self.client.request("GET", "/api/me")

    def create_api_key(self, label=None):
        payload = {}

        if label is not None:
            payload["label"] = label

        return self.client.request(
            "POST",
            "/api/me/api-key",
            json=payload,
        )
