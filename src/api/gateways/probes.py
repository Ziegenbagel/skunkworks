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

    def autonomous_units(self, probe_id, *, limit=500, cursor=None):
        """Observe deployed Manny and Others auxiliary units (API v128)."""

        params = {"limit": int(limit)}
        if cursor:
            params["cursor"] = str(cursor)
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/sector/autonomous-units",
            params=params,
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

    def launch_missile(self, probe_id, actor_manny_id, missile_item_id, target_id):
        """Start the API v125 one-minute Manny missile preparation."""

        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/mannies/{actor_manny_id}/ignite_missile",
            json={
                "missileItemId": str(missile_item_id),
                "targetId": str(target_id),
            },
        )

    def missile(self, probe_id, missile_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/missiles/{missile_id}",
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

    def share_improvement_blueprint(
        self, probe_id, improvement_id, recipient_probe_id,
    ):
        """Share a known blueprint over common active SCUT coverage (API v113+)."""

        return self.client.request(
            "POST",
            (
                f"/api/probe/{probe_id}/probe-improvement-blueprints/"
                f"{improvement_id}/share"
            ),
            json={"recipientProbeId": int(recipient_probe_id)},
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

    def delete_alert(self, probe_id, alert_id):
        """Delete one persistent alert owned by the selected probe (API v112+)."""

        return self.client.request(
            "DELETE",
            f"/api/probe/{probe_id}/alerts/{alert_id}",
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

    def delete_damage_warning(self, probe_id, warning_id):
        """Delete one damage warning owned by the selected probe (API v112+)."""

        return self.client.request(
            "DELETE",
            (
                f"/api/probe/{probe_id}/damage-warnings/"
                f"{warning_id}"
            ),
        )

    def launch_asteroid_trajectory(self, probe_id, asteroid_id, payload):
        """Launch a motorized asteroid on a v111 trajectory."""

        return self.client.request(
            "POST",
            (
                f"/api/probe/{probe_id}/asteroids/"
                f"{asteroid_id}/trajectories"
            ),
            json=payload,
        )

    def asteroid_trajectory(self, probe_id, trajectory_id):
        """Read locally detectable telemetry for a v111 asteroid trajectory."""

        return self.client.request(
            "GET",
            (
                f"/api/probe/{probe_id}/asteroid-trajectories/"
                f"{trajectory_id}"
            ),
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
