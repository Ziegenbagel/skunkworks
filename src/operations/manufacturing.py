from math import ceil


class ManufacturingService:
    """
    Answers manufacturing questions using live recipes and probe inventory.
    """

    def __init__(self, world, recipes):
        self.world = world
        self.recipes = recipes

    def build_report(self, recipe_id):
        """Return a complete manufacturing report for a recipe."""

        recipe = self.recipes.get(recipe_id)

        if recipe is None:
            return None

        return {
            "recipe": recipe,
            "dependencies": self.dependencies(recipe_id),
            "raw_resources": self.raw_resources(recipe_id),
            "dependency_tree": self.dependency_tree(recipe_id),
            "missing_ingredients": self.missing_ingredients(
                recipe_id
            ),
            "production_plan": self.production_plan(
                recipe_id
            ),
        }

    def can_build(self, recipe_id):
        """Return whether the recipe can start from current inventory."""

        missing = self.missing_ingredients(recipe_id)

        if missing is None:
            return False

        return not missing["resources"] and not missing["items"]

    def raw_resources(self, recipe_id):
        """Return recursively required raw resources."""

        if self.recipes.get(recipe_id) is None:
            return None

        totals = {}
        self._collect_raw_resources(recipe_id, totals, set())
        return totals

    def missing_resources(self, recipe_id):
        """Return direct raw-resource shortages for a recipe."""

        missing = self.missing_ingredients(recipe_id)

        if missing is None:
            return None

        return missing["resources"]

    def dependencies(self, recipe_id):
        """Return item ingredients required directly by a recipe."""

        recipe = self.recipes.get(recipe_id)

        if recipe is None:
            return None

        return {
            ingredient["type"]: ingredient["quantity"]
            for ingredient in recipe["ingredients"]
            if self._ingredient_kind(ingredient) == "item"
        }

    def missing_ingredients(self, recipe_id):
        """Return direct resource and item shortages for a recipe."""

        recipe = self.recipes.get(recipe_id)

        if recipe is None:
            return None

        resources, items = self._inventory()
        missing = {"resources": {}, "items": {}}

        for ingredient in recipe["ingredients"]:
            ingredient_type = ingredient["type"]
            required = ingredient["quantity"]
            kind = self._ingredient_kind(ingredient)
            available = (
                resources.get(ingredient_type, 0)
                if kind == "resource"
                else items.get(ingredient_type, 0)
            )

            if available < required:
                missing[kind + "s"][ingredient_type] = round(
                    required - available,
                    3,
                )

        return missing

    def dependency_tree(self, recipe_id):
        """Return the recursive recipe dependency tree for an item."""

        if self.recipes.get(recipe_id) is None:
            return None

        return self._dependency_tree(recipe_id, set())

    def production_plan(self, recipe_id, quantity=1):
        """
        Build an inventory-aware, dependency-first production plan.
        """

        if self.recipes.get(recipe_id) is None:
            return None

        if quantity < 1 or int(quantity) != quantity:
            raise ValueError(
                "Production quantity must be a positive integer."
            )

        resources, items = self._inventory()
        required_resources = {}
        uncraftable_items = {}
        steps = []
        step_positions = {}

        self._plan_recipe(
            recipe_id,
            int(quantity),
            items,
            required_resources,
            uncraftable_items,
            steps,
            step_positions,
            set(),
        )

        missing_resources = {}

        for resource, required in required_resources.items():
            available = resources.get(resource, 0)

            if available < required:
                missing_resources[resource] = round(
                    required - available,
                    3,
                )

        return {
            "target": recipe_id,
            "quantity": int(quantity),
            "steps": steps,
            "required_resources": self._rounded(
                required_resources
            ),
            "missing_resources": missing_resources,
            "uncraftable_items": uncraftable_items,
            "achievable": (
                not missing_resources
                and not uncraftable_items
            ),
        }

    def _dependency_tree(self, recipe_id, ancestors):
        if recipe_id in ancestors:
            raise ValueError(
                f"Circular recipe dependency: {recipe_id}"
            )

        recipe = self.recipes.get(recipe_id)
        branch = ancestors | {recipe_id}
        children = []

        for ingredient in recipe["ingredients"]:
            child = {
                "type": ingredient["type"],
                "kind": self._ingredient_kind(ingredient),
                "quantity": ingredient["quantity"],
            }

            if (
                child["kind"] == "item"
                and child["type"] in self.recipes
            ):
                child["recipe"] = self._dependency_tree(
                    child["type"],
                    branch,
                )

            children.append(child)

        return {
            "id": recipe_id,
            "name": recipe["name"],
            "children": children,
        }

    def _collect_raw_resources(
        self,
        recipe_id,
        totals,
        ancestors,
        multiplier=1,
    ):
        if recipe_id in ancestors:
            raise ValueError(
                f"Circular recipe dependency: {recipe_id}"
            )

        recipe = self.recipes.get(recipe_id)
        branch = ancestors | {recipe_id}

        for ingredient in recipe["ingredients"]:
            amount = ingredient["quantity"] * multiplier

            if self._ingredient_kind(ingredient) == "resource":
                ingredient_type = ingredient["type"]
                totals[ingredient_type] = (
                    totals.get(ingredient_type, 0) + amount
                )
            elif ingredient["type"] in self.recipes:
                self._collect_raw_resources(
                    ingredient["type"],
                    totals,
                    branch,
                    amount,
                )

    def _plan_recipe(
        self,
        recipe_id,
        quantity,
        inventory_items,
        required_resources,
        uncraftable_items,
        steps,
        step_positions,
        ancestors,
    ):
        if recipe_id in ancestors:
            raise ValueError(
                f"Circular recipe dependency: {recipe_id}"
            )

        recipe = self.recipes.get(recipe_id)
        branch = ancestors | {recipe_id}

        for ingredient in recipe["ingredients"]:
            ingredient_type = ingredient["type"]
            required = ingredient["quantity"] * quantity

            if self._ingredient_kind(ingredient) == "resource":
                required_resources[ingredient_type] = (
                    required_resources.get(ingredient_type, 0)
                    + required
                )
                continue

            available = inventory_items.get(ingredient_type, 0)
            consumed = min(available, required)
            inventory_items[ingredient_type] = (
                available - consumed
            )
            shortage = required - consumed

            if shortage <= 0:
                continue

            if ingredient_type not in self.recipes:
                uncraftable_items[ingredient_type] = (
                    uncraftable_items.get(ingredient_type, 0)
                    + shortage
                )
                continue

            self._plan_recipe(
                ingredient_type,
                ceil(shortage),
                inventory_items,
                required_resources,
                uncraftable_items,
                steps,
                step_positions,
                branch,
            )

        self._add_plan_step(
            recipe,
            quantity,
            steps,
            step_positions,
        )

    def _add_plan_step(
        self,
        recipe,
        quantity,
        steps,
        step_positions,
    ):
        recipe_id = recipe["id"]

        if recipe_id in step_positions:
            position = step_positions[recipe_id]
            steps[position]["quantity"] += quantity
            return

        step_positions[recipe_id] = len(steps)
        steps.append(
            {
                "recipe_id": recipe_id,
                "name": recipe["name"],
                "quantity": quantity,
                "craftable_by": tuple(
                    recipe.get("craftableBy", [])
                ),
            }
        )

    def _rounded(self, values):
        return {
            key: round(value, 3)
            for key, value in values.items()
        }

    def _inventory(self):
        inventory = self.world.probe["inventory"]
        resources = {
            stock["type"]: stock["amount"]
            for stock in inventory.get("resourceStocks", [])
        }
        items = {}

        for item in inventory.get("items", []):
            item_type = item["type"]
            items[item_type] = items.get(item_type, 0) + 1

        return resources, items

    def _ingredient_kind(self, ingredient):
        kind = ingredient.get("kind")

        if kind is not None:
            return kind

        if ingredient["type"] in self.recipes:
            return "item"

        return "resource"
