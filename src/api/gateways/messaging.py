"""Probe and inhabited-planet messaging controls."""


class MessagingGateway:
    def __init__(self, client):
        self.client = client

    def received(self, probe_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/messages",
        )

    def sent(self):
        return self.client.request(
            "GET",
            "/api/probe/messages/sent",
        )

    def send(self, probe_id, payload):
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/messages",
            json=payload,
        )

    def mark_read(self, probe_id, message_id):
        return self.client.request(
            "PATCH",
            (
                f"/api/probe/{probe_id}/messages/"
                f"{message_id}/read"
            ),
        )
