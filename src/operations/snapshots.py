class SnapshotService:
    """
    Operational information about the current snapshot.
    """

    def __init__(self, world):
        self.world = world

    def current(self):
        return self.world.snapshot

    def probe_name(self):
        return self.current()["probe"]

    def age(self):
        return self.current()["age"]

    def age_seconds(self):
        return self.current()["age_seconds"]

    def is_fresh(self):
        return self.current()["fresh"]