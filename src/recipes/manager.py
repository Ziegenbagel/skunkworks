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

        return tuple(self._recipes.values())

    def raw_ingredients(self, recipe_id):
        """Expand a recipe tree into total raw-resource requirements."""
        totals = {}

        def expand(identifier, multiplier, ancestry):
            recipe = self.get(identifier)
            if recipe is None or identifier in ancestry:
                return
            for ingredient in recipe.get("ingredients", ()):
                ingredient_type = ingredient.get("type") or ingredient.get("id")
                quantity = float(ingredient.get("quantity", 0) or 0) * multiplier
                kind = str(ingredient.get("kind", "resource"))
                if kind == "resource":
                    totals[ingredient_type] = totals.get(ingredient_type, 0) + quantity
                elif self.get(ingredient_type) is not None:
                    expand(ingredient_type, quantity, ancestry | {identifier})

        expand(recipe_id, 1, set())
        return tuple(
            {"type": resource, "name": resource.replace("_", " ").title(), "quantity": quantity}
            for resource, quantity in sorted(totals.items())
        )

    def ids(self):
        """
        Return all available recipe IDs.
        """

        return tuple(self._recipes.keys())

    def __contains__(self, recipe_id):
        return recipe_id in self._recipes

    def __len__(self):
        return len(self._recipes)
