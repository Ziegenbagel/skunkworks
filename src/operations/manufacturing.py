from math import ceil


class ManufacturingService:
    """
    Mirror the server's recursive, single-order crafting analysis.
    """

    def __init__(self, world, recipes):
        self.world = world
        self.recipes = recipes

    def build_report(self, recipe_id):
        """Return operational and explanatory manufacturing intelligence."""

        recipe = self.recipes.get(recipe_id)

        if recipe is None:
            return None

        order = self.production_plan(recipe_id)

        return {
            "recipe": recipe,
            "dependencies": self.dependencies(recipe_id),
            "dependency_tree": self.dependency_tree(recipe_id),
            "production_plan": order,
            "raw_resources": order["required_resources"],
            "missing_ingredients": {
                "resources": order["missing_resources"],
                "items": order["uncraftable_items"],
            },
        }

    def can_build(self, recipe_id):
        """Return whether one server craft order can start now."""

        plan = self.production_plan(recipe_id)
        return plan is not None and plan["achievable"]

    def raw_resources(self, recipe_id):
        """Return recursive costs after reusing current item inventory."""

        plan = self.production_plan(
            recipe_id,
            include_operational_constraints=False,
        )

        if plan is None:
            return None

        return plan["required_resources"]

    def missing_resources(self, recipe_id):
        plan = self.production_plan(recipe_id)

        if plan is None:
            return None

        return plan["missing_resources"]

    def missing_ingredients(self, recipe_id):
        plan = self.production_plan(recipe_id)

        if plan is None:
            return None

        return {
            "resources": plan["missing_resources"],
            "items": plan["uncraftable_items"],
        }

    def dependencies(self, recipe_id):
        """Return direct item ingredients for explanatory displays."""

        recipe = self.recipes.get(recipe_id)

        if recipe is None:
            return None

        return {
            ingredient["type"]: ingredient["quantity"]
            for ingredient in recipe["ingredients"]
            if self._ingredient_kind(ingredient) == "item"
        }

    def dependency_tree(self, recipe_id):
        """Return the complete explanatory recipe dependency tree."""

        if self.recipes.get(recipe_id) is None:
            return None

        return self._dependency_tree(recipe_id, set())

    def production_plan(
        self,
        recipe_id,
        quantity=1,
        include_operational_constraints=True,
    ):
        """
        Analyze repeated server craft orders without inventing sub-orders.
        """

        recipe = self.recipes.get(recipe_id)

        if recipe is None:
            return None

        if quantity < 1 or int(quantity) != quantity:
            raise ValueError(
                "Production quantity must be a positive integer."
            )

        resources, item_pool = self._inventory()
        required_resources = {}
        consumed_items = []
        synthesized = {}
        uncraftable_items = {}
        duration_seconds = 0

        for _ in range(int(quantity)):
            duration_seconds += self._resolve_recipe(
                recipe_id,
                item_pool,
                required_resources,
                consumed_items,
                synthesized,
                uncraftable_items,
                set(),
            )

        missing_resources = self._missing_resources(
            required_resources,
            resources,
        )
        blockers = []

        if missing_resources:
            blockers.append("missing_resources")

        if uncraftable_items:
            blockers.append("uncraftable_items")

        if include_operational_constraints:
            blockers.extend(
                self._operational_blockers(
                    recipe,
                    int(quantity),
                    required_resources,
                    consumed_items,
                )
            )

        return {
            "target": recipe_id,
            "quantity": int(quantity),
            "orders": [
                {
                    "recipe_id": recipe_id,
                    "quantity": int(quantity),
                    "craftable_by": tuple(
                        recipe.get("craftableBy", [])
                    ),
                }
            ],
            "synthesized_components": synthesized,
            "consumed_inventory_items": self._item_counts(
                consumed_items
            ),
            "required_resources": self._rounded(
                required_resources
            ),
            "missing_resources": missing_resources,
            "uncraftable_items": self._rounded(
                uncraftable_items
            ),
            "duration_seconds": duration_seconds,
            "blockers": tuple(dict.fromkeys(blockers)),
            "achievable": not blockers,
        }

    def _resolve_recipe(
        self,
        recipe_id,
        item_pool,
        required_resources,
        consumed_items,
        synthesized,
        uncraftable_items,
        ancestors,
    ):
        if recipe_id in ancestors:
            raise ValueError(
                f"Circular recipe dependency: {recipe_id}"
            )

        recipe = self.recipes.get(recipe_id)
        branch = ancestors | {recipe_id}
        duration = int(recipe.get("durationSeconds", 0))

        for ingredient in recipe["ingredients"]:
            ingredient_type = ingredient["type"]
            required = ingredient["quantity"]

            if self._ingredient_kind(ingredient) == "resource":
                required_resources[ingredient_type] = (
                    required_resources.get(ingredient_type, 0)
                    + required
                )
                continue

            required_count = ceil(required)
            available = item_pool.get(ingredient_type, [])
            consumed_count = min(
                required_count,
                len(available),
            )

            for _ in range(consumed_count):
                consumed_items.append(available.pop())

            missing_count = required_count - consumed_count

            if missing_count <= 0:
                continue

            component = self.recipes.get(ingredient_type)

            if component is None or not component.get(
                "craftableBy"
            ):
                uncraftable_items[ingredient_type] = (
                    uncraftable_items.get(ingredient_type, 0)
                    + missing_count
                )
                continue

            synthesized[ingredient_type] = (
                synthesized.get(ingredient_type, 0)
                + missing_count
            )

            for _ in range(missing_count):
                duration += self._resolve_recipe(
                    ingredient_type,
                    item_pool,
                    required_resources,
                    consumed_items,
                    synthesized,
                    uncraftable_items,
                    branch,
                )

        return duration

    def _operational_blockers(
        self,
        recipe,
        quantity,
        required_resources,
        consumed_items,
    ):
        blockers = []
        probe = self.world.probe

        if not probe.get("telemetry_available", True):
            return ["probe_out_of_range"]

        if probe["status"] != "idle":
            blockers.append("probe_unavailable")

        fabricators = recipe.get("craftableBy", [])

        if not any(
            self._fabricator_available(fabricator)
            for fabricator in fabricators
        ):
            blockers.append("fabricator_unavailable")

        inventory = probe["inventory"]
        freed_capacity = sum(
            amount
            for resource, amount in required_resources.items()
            if resource != "deuterium"
        )
        freed_capacity += sum(
            item.get("containerSpace", 0)
            for item in consumed_items
        )
        output_space = (
            recipe.get("output", {}).get("containerSpace", 0)
            * quantity
        )
        free_after_consumption = (
            inventory.get("freeCapacity", 0)
            + freed_capacity
        )

        if free_after_consumption + 0.00001 < output_space:
            blockers.append("insufficient_cargo_capacity")

        return blockers

    def _fabricator_available(self, fabricator):
        idle_mannies = self._idle_onboard_mannies()

        if fabricator == "manny":
            return bool(idle_mannies)

        if fabricator == "atomic_3d_printer":
            printer = next(
                (
                    item
                    for item in self.world.probe[
                        "inventory"
                    ].get("items", [])
                    if item["type"] == "atomic_3d_printer"
                ),
                None,
            )
            return (
                printer is not None
                and printer.get("currentTask") is None
                and bool(idle_mannies)
            )

        return False

    def _idle_onboard_mannies(self):
        return [
            manny
            for manny in self.world.mannies.get(
                "mannies",
                [],
            )
            if manny.get("currentTask") is None
            and manny.get("canReceiveOrders", False)
            and manny.get("location", {}).get("type") == "probe"
        ]

    def _inventory(self):
        probe = self.world.probe
        inventory = probe["inventory"]
        resources = {
            stock["type"]: stock["amount"]
            for stock in inventory.get("resourceStocks", [])
        }
        resources["deuterium"] = probe["fuel"].get(
            "deuterium",
            0,
        )
        item_pool = {}

        for item in inventory.get("items", []):
            item_pool.setdefault(item["type"], []).append(
                item.copy()
            )

        return resources, item_pool

    def _missing_resources(self, required, available):
        return {
            resource: round(amount - available.get(resource, 0), 3)
            for resource, amount in required.items()
            if available.get(resource, 0) < amount
        }

    def _item_counts(self, items):
        counts = {}

        for item in items:
            item_type = item["type"]
            counts[item_type] = counts.get(item_type, 0) + 1

        return counts

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

    def _ingredient_kind(self, ingredient):
        return ingredient.get(
            "kind",
            (
                "item"
                if ingredient.get("unit") == "item"
                else "resource"
            ),
        )

    def _rounded(self, values):
        return {
            key: round(value, 3)
            for key, value in values.items()
        }
