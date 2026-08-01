"""Probe telemetry, movement, logs, alerts, and improvements."""


class ProbeGateway:
    def __init__(self, client):
        self.client = client

    def list(self):
        return self.client.request("GET", "/api/probes")

    def get(self, probe_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}",
        )

    def update(self, probe_id, **changes):
        return self.client.request(
            "PATCH",
            f"/api/probe/{probe_id}",
            json=changes,
        )

    def make_default(self, probe_id):
        return self.update(probe_id, isDefault=True)

    def sector(self, probe_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/sector",
        )

    def move(self, probe_id, target):
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/move",
            json={"target": target},
        )

    def cancel_move(self, probe_id):
        """Cancel an active movement while it is still preparing (API v105+)."""

        return self.client.request(
            "DELETE",
            f"/api/probe/{probe_id}/move",
        )

    def visited_sectors(self, probe_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/visited-sectors",
        )

    def improvements(self, probe_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/probe-improvements-available",
        )

    def scut_network(self, probe_id, network_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/scut-network/{network_id}",
        )

    def alerts(self, probe_id, status=None):
        params = {"status": status} if status is not None else None
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/alerts",
            **({"params": params} if params else {}),
        )

    def update_alert(self, probe_id, alert_id, **changes):
        return self.client.request(
            "PATCH",
            f"/api/probe/{probe_id}/alerts/{alert_id}",
            json=changes,
        )

    def damage_warnings(self, probe_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/damage-warnings",
        )

    def update_damage_warning(
        self,
        probe_id,
        warning_id,
        **changes,
    ):
        return self.client.request(
            "PATCH",
            (
                f"/api/probe/{probe_id}/damage-warnings/"
                f"{warning_id}"
            ),
            json=changes,
        )

    def logbook_pages(self, probe_id, limit=100, offset=0):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/logbook-pages",
            params={"limit": limit, "offset": offset},
        )

    def create_logbook_page(self, probe_id, payload):
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/logbook-page",
            json=payload,
        )

    def get_logbook_page(self, probe_id, page_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/logbook-page/{page_id}",
        )

    def update_logbook_page(
        self,
        probe_id,
        page_id,
        payload,
    ):
        return self.client.request(
            "PATCH",
            f"/api/probe/{probe_id}/logbook-page/{page_id}",
            json=payload,
        )

    def delete_logbook_page(self, probe_id, page_id):
        return self.client.request(
            "DELETE",
            f"/api/probe/{probe_id}/logbook-page/{page_id}",
        )
