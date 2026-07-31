"""Complete Manny and atomic-printer control surface."""


class MannyGateway:
    TASK_ROUTES = frozenset(
        {
            "repair",
            "mine",
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

    def atomic_printer_craft(self, probe_id, recipe_id):
        return self.client.request(
            "POST",
            f"/api/probe/{probe_id}/atomic-printer/craft",
            json={"recipe": recipe_id},
        )
