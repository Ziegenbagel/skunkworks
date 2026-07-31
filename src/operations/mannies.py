"""First-class operational questions about Manny workers."""

from datetime import UTC, datetime


class MannyService:
    def __init__(self, world):
        self.world = world

    def all(self):
        return tuple(self.world.mannies.get("mannies", ()))

    def total(self):
        return len(self.all())

    def idle(self):
        return tuple(
            manny for manny in self.all()
            if manny.get("currentTask") is None
        )

    def available(self):
        return tuple(
            manny for manny in self.idle()
            if manny.get("canReceiveOrders", False)
        )

    def by_task(self, task):
        return tuple(
            manny for manny in self.all()
            if self._task_type(manny) == task
        )

    def mining(self):
        return self.by_task("mining")

    def manufacturing(self):
        return tuple(
            manny for manny in self.all()
            if self._task_type(manny) in {
                "crafting",
                "assisting_atomic_printer",
                "assembling_probe",
            }
        )

    def deployed(self):
        return tuple(
            manny for manny in self.all()
            if (manny.get("location") or {}).get("type") != "probe"
        )

    def assigned_to_probe(self, probe_id):
        return tuple(
            manny for manny in self.all()
            if (manny.get("location") or {}).get("probeId") == probe_id
        )

    def progress(self):
        return {
            manny["id"]: manny.get("taskProgressPercent", 0)
            for manny in self.all()
            if manny.get("currentTask") is not None
        }

    def next_completion(self):
        candidates = []
        for manny in self.all():
            task = manny.get("currentTask") or {}
            raw = (
                task.get("endsAt")
                or task.get("expectedCompletionAt")
                or manny.get("taskEndsAt")
            )
            if raw:
                try:
                    instant = datetime.fromisoformat(
                        raw.replace("Z", "+00:00")
                    )
                except (TypeError, ValueError):
                    continue
                candidates.append((instant, manny))
        if not candidates:
            return None
        instant, manny = min(candidates, key=lambda item: item[0])
        return {
            "manny": manny,
            "at": instant.astimezone(UTC),
        }

    @staticmethod
    def _task_type(manny):
        task = manny.get("currentTask")
        return task.get("type") if isinstance(task, dict) else task
