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

        order = self.production_plan(recipe_id, use_inventory_items=False)

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

        plan = self.production_plan(recipe_id, use_inventory_items=False)
        return plan is not None and plan["achievable"]

    def inventory_count(self, item_type, include_active=True):
        """Return completed inventory plus optionally active production."""

        if item_type == "manny":
            completed = len(
                self.world.mannies.get("mannies", [])
            )
            return completed

        completed = sum(
            self._item_quantity(item)
            for item in self.world.probe[
                "inventory"
            ].get("items", [])
            if item["type"] == item_type
        )
        return completed + (
            self.active_production_count(item_type)
            if include_active else 0
        )

    def active_production_count(self, item_type):
        """Count observable craft outputs that have started but not completed."""

        count = 0
        for manny in self.world.mannies.get("mannies", []):
            if self._active_recipe(manny) == item_type:
                count += 1
        for item in self.world.probe.get("inventory", {}).get("items", []):
            if item.get("type") != "atomic_3d_printer":
                continue
            if self._active_recipe(item) == item_type:
                count += 1
        return count

    def _active_recipe(self, asset):
        current = asset.get("currentTask")
        if isinstance(current, dict):
            details = current
            task_type = current.get("type")
        else:
            # The API may retain the detail of the previous task after a Manny
            # becomes idle or starts different work. currentTask is the
            # authoritative activity flag; task only describes that activity.
            task_type = current
            details = asset.get("task") if isinstance(asset.get("task"), dict) else {}
        if task_type not in {"crafting", "assisting_atomic_printer"}:
            return None
        reference = (
            details.get("recipe")
            or details.get("recipeId")
            or details.get("recipeName")
            or details.get("output")
        )
        if isinstance(reference, dict):
            reference = reference.get("id") or reference.get("type") or reference.get("name")
        if reference in self.recipes:
            return reference
        normalized = str(reference or "").strip().lower().replace(" ", "_")
        for recipe in self.recipes.all():
            if normalized in {
                str(recipe.get("id", "")).lower(),
                str(recipe.get("name", "")).strip().lower().replace(" ", "_"),
                str((recipe.get("output") or {}).get("type", "")).lower(),
            }:
                return recipe.get("id")
        return normalized or None

    def raw_resources(self, recipe_id):
        """Return the complete recursive raw-resource cost of one order."""

        plan = self.production_plan(
            recipe_id,
            include_operational_constraints=False,
            use_inventory_items=False,
        )

        if plan is None:
            return None

        return plan["required_resources"]

    def missing_resources(self, recipe_id):
        plan = self.production_plan(recipe_id, use_inventory_items=False)

        if plan is None:
            return None

        return plan["missing_resources"]

    def missing_ingredients(self, recipe_id):
        plan = self.production_plan(recipe_id, use_inventory_items=False)

        if plan is None:
            return None

        return {
            "resources": plan["missing_resources"],
            "items": plan["uncraftable_items"],
        }

    def available_inputs(self):
        """Return copy-safe resource amounts and item counts for allocation."""

        resources, items = self._inventory()
        return resources, {
            item_type: len(entries)
            for item_type, entries in items.items()
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
        protected_items=None,
        use_inventory_items=False,
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
        if not use_inventory_items:
            # The game accepts an ordinary craft as one direct recipe and
            # resolves all nested craftable ingredients from raw resources.
            # Stored crafted components are physical assembly inventory; they
            # must never be borrowed by Manny or atomic-printer recipes.
            item_pool = {}
        for item_type, protected_count in (protected_items or {}).items():
            available = item_pool.get(item_type, [])
            if available and protected_count:
                # Assembly allocations remain in inventory but are invisible to
                # ordinary recipe analysis. The server can then satisfy the
                # direct target recipe from recursively calculated raw inputs.
                del available[max(0, len(available) - int(protected_count)):]
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
            "protected_inventory_items": dict(protected_items or {}),
        }

    def production_bundle_plan(self, requests, use_inventory_items=False):
        """Resolve several recipe quantities against one shared inventory pool."""

        normalized = {
            recipe_id: int(quantity)
            for recipe_id, quantity in requests.items()
            if quantity and int(quantity) == quantity and int(quantity) > 0
        }
        if not normalized:
            return {
                "required_resources": {},
                "missing_resources": {},
                "consumed_inventory_items": {},
                "synthesized_components": {},
                "uncraftable_items": {},
            }
        if any(self.recipes.get(recipe_id) is None for recipe_id in normalized):
            return None

        resources, item_pool = self._inventory()
        if not use_inventory_items:
            item_pool = {}
        required_resources = {}
        consumed_items = []
        synthesized = {}
        uncraftable_items = {}
        for recipe_id, quantity in normalized.items():
            for _ in range(quantity):
                self._resolve_recipe(
                    recipe_id,
                    item_pool,
                    required_resources,
                    consumed_items,
                    synthesized,
                    uncraftable_items,
                    set(),
                )
        return {
            "required_resources": self._rounded(required_resources),
            "missing_resources": self._missing_resources(required_resources, resources),
            "consumed_inventory_items": self._item_counts(consumed_items),
            "synthesized_components": synthesized,
            "uncraftable_items": self._rounded(uncraftable_items),
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
            for stack_index in range(self._item_quantity(item)):
                entry = item.copy()
                # Dependency allocation consumes units, not API stack rows.
                entry["quantity"] = 1
                entry["stackIndex"] = stack_index
                item_pool.setdefault(item["type"], []).append(entry)

        return resources, item_pool

    @staticmethod
    def _item_quantity(item):
        value = item.get("quantity", item.get("count", 1))
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 1

    def _missing_resources(self, required, available):
        # Resource quantities are authoritative to three decimal ECE places.
        # Comparing the unrounded binary floats first could retain a positive
        # sub-milliscale residue (for example 3.7800000000000002 required
        # versus 3.78 onboard), then round its displayed shortage to 0.000.
        # The non-empty mapping still blocked the craft indefinitely despite
        # the UI correctly showing every input fully covered.
        missing = {}
        for resource, amount in required.items():
            shortage = round(
                float(amount) - float(available.get(resource, 0) or 0), 3,
            )
            if shortage > 0:
                missing[resource] = shortage
        return missing

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
