from src.knowledge.crafting import (
    CraftingKnowledge,
)


class ManufacturingReport:
    """
    Builds a complete manufacturing report
    for a craftable item.
    """

    def __init__(self):

        self.crafting = (
            CraftingKnowledge()
        )

    def build(
        self,
        item_name,
    ):

        recipe = self.crafting.get_recipe(
            item_name
        )

        if recipe is None:

            return None

        return {
            "recipe": recipe,
            "dependencies": (
                self.crafting.get_dependencies(
                    item_name
                )
            ),
            "raw_resources": (
                self.crafting.get_total_raw_resources(
                    item_name
                )
            ),
            "dependency_tree": (
                self.crafting.get_dependency_tree(
                    item_name
                )
            ),
        }