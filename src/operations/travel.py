from src.knowledge.movement import MovementKnowledge


class TravelService:
    """Operational travel intelligence."""

    def __init__(self, world):
        self.world = world
        self.knowledge = MovementKnowledge()

    def fuel_available(self):
        return self.world.probe["fuel"].get(
            "deuterium",
            0,
        )

    def fuel_cost(self):
        return self.knowledge.fuel_cost()

    def fuel_percentage(self):
        fuel = self.world.probe["fuel"]
        maximum = fuel.get("maxDeuterium", 0)

        if maximum <= 0:
            return 0

        return fuel.get("deuterium", 0) / maximum * 100

    def travel_ready(self):
        return (
            self.world.probe["telemetry_available"]
            and self.world.probe["status"] == "idle"
            and self.fuel_available() >= self.fuel_cost()
        )
