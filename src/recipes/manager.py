class RecipeManager:
    """
    Stores and provides access to crafting recipes.
    """

    def __init__(self):
        self._recipes = {}

    def load(self, recipes):
        """
        Load recipes from the API response.
        """

        self._recipes = {
            recipe["id"]: recipe
            for recipe in recipes["recipes"]
        }

    def get(self, recipe_id):
        """
        Return a recipe by ID.
        """

        return self._recipes.get(recipe_id)

    def all(self):
        """
        Return all loaded recipes.
        """

        return self._recipes.values()

    def ids(self):
        """
        Return all available recipe IDs.
        """

        return self._recipes.keys()

    def __contains__(self, recipe_id):
        return recipe_id in self._recipes

    def __len__(self):
        return len(self._recipes)