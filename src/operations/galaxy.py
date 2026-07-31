"""Operational access to the durable galaxy map."""


class GalaxyService:
    def __init__(self, world):
        self.world = world

    def known_sectors(self):
        if self.world.galaxy is None:
            return ()

        return self.world.galaxy.sectors()

    def known_sector_count(self):
        return len(self.known_sectors())

    def sector(self, coordinates):
        if self.world.galaxy is None:
            return None

        return self.world.galaxy.get(coordinates)

    def visited(self, coordinates):
        record = self.sector(coordinates)
        return record is not None and record.visit_count > 0
