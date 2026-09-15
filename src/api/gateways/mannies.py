"""Complete Manny and atomic-printer control surface."""


class MannyGateway:
    TASK_ROUTES = frozenset(
        {
            "repair",
            "mine",
            "motorize-asteroid",
            "refuel-motorized-asteroid",
            "sculpt-duck-asteroid",
            "craft",
            "salvage",
            "install-bookmark",
            "detach-storage-container",
            "drop-storage-container",
            "drop-manny-cargo",
            "inspect-sector-object",
            "recover-storage-container",
            "refill-deuterium-tank",
            "transfer-deuterium-to-probe",
            "transfer-to-probe",
            "turn-on-relay",
            "install-scut-transit-beacon",
            "improve-probe",
            "assemble-probe",
            "recall",
        }
    )

    def __init__(self, client):
        self.client = client

    def list(self, probe_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/mannies",
        )

    def get(self, probe_id, manny_id):
        if getattr(self.client, "api_version", 104) < 104:
            response = self.list(probe_id)
            manny = next(
                (
                    candidate
                    for candidate in response.get(
                        "mannies",
                        [],
                    )
                    if candidate["id"] == manny_id
                ),
                None,
            )

            if manny is None:
                raise LookupError(
                    f"Manny {manny_id} was not found."
                )

            return {
                "manny": manny,
                "nextUsefulRefreshDelayMs": response.get(
                    "nextUsefulRefreshDelayMs",
                    30000,
                ),
            }

        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/mannies/{manny_id}",
        )

    def rename(self, probe_id, manny_id, name):
        return self.client.request(
            "PATCH",
            f"/api/probe/{probe_id}/mannies/{manny_id}",
            json={"name": name},
        )

    def start_task(
        self,
        probe_id,
        manny_id,
        task,
        payload=None,
    ):
        if task not in self.TASK_ROUTES:
            raise ValueError(f"Unknown Manny task: {task}")

        return self.client.request(
            "POST",
            (
                f"/api/probe/{probe_id}/mannies/"
                f"{manny_id}/{task}"
            ),
            json=payload or {},
        )

    def start_tasks(self, probe_id, tasks):
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/mannies/tasks",
            json={"tasks": tasks},
        )

    def sector_storage_inventory(self, probe_id, object_id, limit=100, cursor=None):
        params = {"limit": int(limit)}
        if cursor:
            params["cursor"] = cursor
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/sector-objects/{object_id}/inventory",
            params=params,
        )

    @staticmethod
    def _idempotency_headers(idempotency_key):
        return {"Idempotency-Key": str(idempotency_key)} if idempotency_key else {}

    def start_storage_transfer(
        self, probe_id, manny_id, payload, idempotency_key=None,
    ):
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/mannies/{manny_id}/storage-transfers",
            json=dict(payload),
            headers=self._idempotency_headers(idempotency_key),
        )

    def transfer_deuterium_from_external_storage(
        self, probe_id, manny_id, object_id, amount, idempotency_key=None,
    ):
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/mannies/{manny_id}/transfer-deuterium-from-external-storage",
            json={"objectId": str(object_id), "amount": float(amount)},
            headers=self._idempotency_headers(idempotency_key),
        )

    def storage_transfer(self, probe_id, transfer_id):
        return self.client.request(
            "GET",
            f"/api/probe/{probe_id}/storage-transfers/{transfer_id}",
        )

    def atomic_printer_craft(self, probe_id, recipe_id, manny_id=None):
        payload = {"recipe": recipe_id}
        if manny_id:
            payload["mannyId"] = str(manny_id)
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/atomic-printer/craft",
            json=payload,
        )
