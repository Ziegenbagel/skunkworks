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
    
    def _normalize_recipe_name(
        self,
        name,
    ):
        """
        Convert recipe references into the
        canonical recipe name used by
        gameplay.json.
        """

        import re

        return re.sub(
            r"(?<!^)(?=[A-Z])",
            "_",
            name,
        ).lower()
    
    def get_dependencies(
        self,
        item_name,
    ):
        """
        Return the crafted components required
        to build an item.
        """

        recipe = self.get_recipe(
            item_name
        )

        if recipe is None:

            return {}

        return recipe[
            "crafted_components"
        ]
    
    def get_dependency_tree(
        self,
        item_name,
    ):
        """
        Build a recursive dependency tree for
        a craftable item.
        """

        return self._get_dependency_tree(
            item_name
        )
    
    def _get_dependency_tree(
        self,
        item_name,
    ):
        """
        Build a recursive dependency tree for
        a craftable item.
        """

        recipe = self.get_recipe(
            item_name
        )

        if recipe is None:

            return None

        tree = {
            "name": item_name,
            "children": [],
        }

        for component, count in (
            recipe[
                "crafted_components"
            ].items()
        ):

            child = self._get_dependency_tree(
                self._normalize_recipe_name(
                    component
                )
            )

            if child is None:

                child = {
                    "name": component,
                    "children": [],
                }

            child["count"] = count

            tree["children"].append(
                child
            )

        return tree
    
    def _collect_resources(
        self,
        item_name,
        totals,
        multiplier=1,
    ):
        """
        Recursively accumulate the total raw
        resources required to craft an item.
        """

        recipe = self.get_recipe(
            item_name
        )

        if recipe is None:

            return

        #
        # Add this recipe's raw resources.
        #

        for resource, amount in (
            recipe[
                "raw_resources"
            ].items()
        ):

            totals[resource] = (
                totals.get(
                    resource,
                    0,
                )
                + (
                    amount
                    * multiplier
                )
            )

        #
        # Recurse into crafted components.
        #

        for component, count in (
            recipe[
                "crafted_components"
            ].items()
        ):

            self._collect_resources(
                self._normalize_recipe_name(
                    component
                ),
                totals,
                multiplier * count,
            )

    def get_total_raw_resources(
        self,
        item_name,
    ):
        """
        Return the total raw resources
        required to manufacture an item.
        """

        totals = {}

        self._collect_resources(
            item_name,
            totals,
        )

        return totals