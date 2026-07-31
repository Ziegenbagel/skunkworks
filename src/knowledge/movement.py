"""Canonical movement rules required by operational reasoning."""

MOVEMENT_FUEL_COST_POINTS = 2.0


class MovementKnowledge:
    """Expose stable movement rules used by operational services."""

    def fuel_cost(self):
        return MOVEMENT_FUEL_COST_POINTS
