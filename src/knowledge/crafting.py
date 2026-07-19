from src.knowledge.gameplay import (
    GameplayKnowledge,
)


class CraftingKnowledge:
    """
    Provides normalized access to crafting
    recipes.
    """

    def __init__(self):

        gameplay = GameplayKnowledge()

        self.crafting = gameplay.data[
            "crafting"
        ]

    def get_recipe(
        self,
        item_name,
    ):

        recipe = self.crafting.get(
            item_name
        )

        if recipe is None:
            return None

        normalized = {
            "name": item_name,
            "description": recipe.get(
                "description",
                "",
            ),
            "duration_seconds": recipe.get(
                "durationSeconds",
                0,
            ),
            "container_space": recipe.get(
                "containerSpace",
                0,
            ),
            "raw_resources": {},
            "crafted_components": {},
            "effects": {},
        }

        for key, value in recipe.items():

            if key.endswith("Cost"):

                resource = key.removesuffix(
                    "Cost"
                )

                normalized[
                    "raw_resources"
                ][resource] = value

            elif key.endswith("Count"):

                component = key.removesuffix(
                    "Count"
                )

                normalized[
                    "crafted_components"
                ][component] = value

            elif key == "cargoCapacity":

                normalized[
                    "effects"
                ]["cargo_capacity"] = value

            elif key == "capacityBonus":

                normalized[
                    "effects"
                ]["capacity_bonus"] = value

        return normalized

    def list_recipes(self):

        return sorted(
            self.crafting.keys()
        )

    def recipe_exists(
        self,
        item_name,
    ):

        return (
            item_name
            in self.crafting
        )