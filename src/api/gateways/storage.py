"""Inventory, container, routing-rule, and stock-move controls."""


class StorageGateway:
    def __init__(self, client):
        self.client = client

    def containers(self, probe_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/storage-containers",
        )

    def container(self, probe_id, container_id):
        return self.client.request(
            "GET",
            (
                f"/api/probe/{probe_id}/storage-containers/"
                f"{container_id}"
            ),
        )

    def update_container(
        self,
        probe_id,
        container_id,
        payload,
    ):
        return self.client.request(
            "PATCH",
            (
                f"/api/probe/{probe_id}/storage-containers/"
                f"{container_id}"
            ),
            json=payload,
        )

    def update_rules(
        self,
        probe_id,
        container_id,
        rules,
    ):
        return self.client.request(
            "PATCH",
            (
                f"/api/probe/{probe_id}/storage-containers/"
                f"{container_id}/rules"
            ),
            json={"rules": rules},
        )

    def reassign_crafting_reservations(self, probe_id, container_id):
        """Atomically move all active craft-output reservations elsewhere."""

        return self.client.request(
            "POST",
            (
                f"/api/probe/{probe_id}/storage-containers/"
                f"{container_id}/crafting-reservations/reassign"
            ),
            json={},
        )

    def move(self, probe_id, payload):
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/storage-moves",
            json=payload,
        )

    def inventory_item(self, probe_id, item_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/inventory/{item_id}",
        )

    def jettison(
        self,
        probe_id,
        item_id,
        amount=None,
        container_id=None,
    ):
        payload = {}

        if amount is not None:
            payload["amount"] = amount

        if container_id is not None:
            payload["containerId"] = container_id

        return self.client.request(
            "POST",
            (
                f"/api/probe/{probe_id}/inventory/"
                f"{item_id}/jettison"
            ),
            json=payload,
        )
