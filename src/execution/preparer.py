"""Prepare, classify, and journal commands without executing them."""

from dataclasses import dataclass

from .policy import ExecutionMode
from .preflight import PreflightValidator
from .translator import TaskCommandTranslator
from src.planner.scheduling import ordered_tasks, task_order_key


@dataclass(frozen=True)
class PreparedCommand:
    command: object
    disposition: str
    blockers: tuple[str, ...] = ()
    warnings: tuple[object, ...] = ()


class CommandPreparer:
    """Build the safe command queue; never calls mutation gateways."""

    def __init__(
        self,
        operations,
        probe_id,
        policy,
        journal=None,
    ):
        self.translator = TaskCommandTranslator(
            operations,
            probe_id,
        )
        self.validator = PreflightValidator(
            operations,
            probe_id,
        )
        self.policy = policy
        self.journal = journal

    def prepare(self, tasks):
        # Preparation may also be called outside the UI controller.  Always
        # replay the same scheduler order here so translation, Manny claims,
        # and input reservations cannot silently invent a second priority
        # model based on caller order.
        tasks = ordered_tasks(tasks)
        prepared = []
        # A non-executable manufacturing goal can still own the raw material
        # already accumulated for its next unit.  Seed those partial claims
        # before translating commands so a cheaper, lower-priority recipe
        # cannot repeatedly spend deliveries mined for the blocked goal.
        resource_claims = self._goal_resource_claims(tasks)
        item_claims = self._goal_item_claims(tasks)
        for task in tasks:
            # Claims made while evaluating one proposal are provisional.  A
            # rejected proposal must not poison every candidate behind it.
            # Seeded assembly-kit claims remain present in these snapshots.
            resource_snapshot = {
                resource: list(claims)
                for resource, claims in resource_claims.items()
            }
            item_snapshot = {
                item_type: list(claims)
                for item_type, claims in item_claims.items()
            }
            reservation_blockers = self._reserve_manufacturing_inputs(
                task, resource_claims, item_claims,
            )
            command = self.translator.translate(task)

            if command is None:
                resource_claims = resource_snapshot
                item_claims = item_snapshot
                continue

            blockers = list(self.validator.blockers(command))
            blockers.extend(reservation_blockers)
            warnings = self.validator.warnings(command)

            if (
                warnings
                and not self.validator.operations
                .travel_safety.policy.allow_risky_travel
            ):
                blockers.append(
                    "travel_risk_disabled_by_player"
                )

            if (
                self.journal is not None
                and self.journal.was_successful(
                    command.fingerprint
                )
            ):
                blockers.append("already_completed")

            # Translation assigns idle Mannys so simultaneously executable
            # commands cannot collide. A command that will not execute must not
            # retain that temporary claim and starve later valid proposals.
            if blockers:
                self.translator.release_claim(command)
                resource_claims = resource_snapshot
                item_claims = item_snapshot

            disposition = self._disposition(
                command,
                blockers,
                warnings,
            )
            item = PreparedCommand(
                command=command,
                disposition=disposition,
                blockers=tuple(blockers),
                warnings=warnings,
            )
            prepared.append(item)

            if self.journal is not None:
                self.journal.record(
                    command,
                    disposition,
                    blockers,
                )

        return tuple(
            prepared[: self.policy.max_commands_per_cycle]
        )

    def manual_manufacturing_blockers(self, recipe_id, planned_tasks):
        """Protect planner allocations before a user starts a manual craft.

        Manual commands intentionally bypass automatic dispatch policy, but
        they must not bypass the resource and completed-item ledger belonging
        to higher-priority goals. Treat the ad-hoc order as lowest priority and
        replay the current planner claims before evaluating one unit.
        """

        from src.planner.task import Task

        tasks = tuple(sorted(planned_tasks, key=task_order_key))
        resource_claims = {}
        item_claims = self._goal_item_claims(tasks)
        for task in tasks:
            self._reserve_manufacturing_inputs(task, resource_claims, item_claims)
        manual = Task(
            action="Craft Item",
            reason="Manual build order",
            target=recipe_id,
            quantity=1,
            priority=11,
        )
        return tuple(self._reserve_manufacturing_inputs(
            manual, resource_claims, item_claims, manual=True,
        ))

    @staticmethod
    def _goal_item_claims(tasks):
        """Seed claims for completed parts committed to assembly goals.

        Every task emitted for the same goal carries the same snapshot, so use
        the maximum claim at each priority rather than adding duplicate copies.
        """

        grouped = {}
        for task in tasks:
            rank = task_order_key(task)
            for item_type, amount in getattr(task, "reserved_items", ()):
                key = (item_type, rank)
                grouped[key] = max(grouped.get(key, 0), int(amount))
        claims = {}
        for (item_type, rank), amount in grouped.items():
            claims.setdefault(item_type, []).append((rank, amount))
        return claims

    def _goal_resource_claims(self, tasks):
        """Seed partial raw-resource claims for blocked production goals.

        ``Prepare Manufacturing`` tasks do not translate into commands, so
        their normal provisional claims would otherwise be rolled back.  Keep
        at most the next unit's currently available inputs.  Equal-ranked
        goals may share them; only lower-ranked work observes the claim.
        """

        manufacturing = self.translator.operations.manufacturing
        grouped = {}
        for task in tasks:
            if task.action != "Prepare Manufacturing" or not task.target:
                continue
            plan = manufacturing.production_plan(
                task.target,
                quantity=1,
                include_operational_constraints=False,
                use_inventory_items=(task.category == "fleet_assembly"),
            )
            if plan is None:
                continue
            missing = plan.get("missing_resources", {})
            if missing and not all(
                self._resource_has_acquisition_path(resource)
                for resource, amount in missing.items()
                if float(amount) > 0
            ):
                # Do not strand unrelated inputs behind a goal whose next
                # unit cannot currently be funded.  A later refresh will seed
                # the claim again as soon as a source or inbound mining
                # commitment for every missing resource becomes available.
                continue
            resources, _items = manufacturing.available_inputs()
            rank = task_order_key(task)
            for resource, required in plan["required_resources"].items():
                amount = min(
                    float(required), float(resources.get(resource, 0)),
                )
                if amount <= 0:
                    continue
                # Several planner entries can describe the same goal
                # snapshot.  Claim the maximum next-unit amount, not their
                # sum, to avoid manufacturing artificial scarcity.
                key = (resource, rank, task.target)
                grouped[key] = max(grouped.get(key, 0.0), amount)

        claims = {}
        for (resource, rank, _target), amount in grouped.items():
            claims.setdefault(resource, []).append((rank, amount))
        return claims

    def _resource_has_acquisition_path(self, resource):
        mining = self.translator.operations.mining
        if mining.best_target(resource) is not None:
            return True
        return float(mining.active_commitments().get(resource, 0)) > 0

    def _reserve_manufacturing_inputs(
        self, task, resource_claims, item_claims, *, manual=False,
    ):
        if task.action not in {"Craft Item", "Prepare Manufacturing"} or not task.target:
            return []
        # The dispatcher starts one craft per proposal. Reserve the inputs for
        # the next unit of a higher-priority goal, not its entire desired batch;
        # otherwise a large long-term target can strand usable surplus and idle
        # fabricators while protected work is already in progress.
        manufacturing = self.translator.operations.manufacturing
        task_rank = task_order_key(task)
        plan = manufacturing.production_plan(
            task.target,
            quantity=1,
            include_operational_constraints=False,
            # Ordinary game recipes are submitted as one direct recursive
            # craft. They synthesize nested ingredients from raw resources and
            # must not be treated as consumers of physical assembly inventory.
            # Fleet-component work is the exception: that chain deliberately
            # works with the stored kit allocated to its assembly goal.
            use_inventory_items=(manual or task.category == "fleet_assembly"),
        )
        if plan is None:
            return []
        resources, items = manufacturing.available_inputs()

        conflicts = []
        for resource, required in plan["required_resources"].items():
            available = float(resources.get(resource, 0))
            claims = resource_claims.setdefault(resource, [])
            higher_claimed = sum(
                amount for rank, amount in claims
                if rank < task_rank
            )
            available_after_higher = max(0, available - higher_claimed)
            if (
                task.action == "Craft Item"
                and available_after_higher + 0.00001 < float(required)
            ):
                conflicts.append("resource_reserved_by_higher_priority_goal")
            claims.append((task_rank, min(float(required), available)))
        for item_type, required in plan["consumed_inventory_items"].items():
            available = int(items.get(item_type, 0))
            claims = item_claims.setdefault(item_type, [])
            higher_claimed = sum(
                amount for rank, amount in claims
                if rank <= task_rank
            )
            available_after_higher = max(0, available - higher_claimed)
            # A component being built for this assembly goal may need to
            # consume another component from the same kit.  That is not theft:
            # the next planning snapshot will see the consumed dependency as
            # missing and rebuild it before assembly.  Blocking it here causes
            # a permanent component-chain deadlock (for example, a linear
            # actuator that consumes the currently stored integrated circuit).
            # Unrelated production and manual orders remain protected.
            owns_assembly_chain = task.category == "fleet_assembly"
            if (
                task.action == "Craft Item"
                and not owns_assembly_chain
                and available_after_higher < int(required)
            ):
                conflicts.append("item_reserved_by_higher_priority_goal")
            claims.append((task_rank, min(int(required), available)))

        # The game may satisfy a recursively submitted recipe from matching
        # physical components already in inventory before synthesizing those
        # components from raw resources.  A raw-resource production plan alone
        # therefore cannot protect a completed probe-assembly kit.  Treat the
        # stored items allocated to equal- or higher-priority assembly work as
        # a hard floor.  A numerically higher-priority craft is intentionally
        # allowed to consume inventory claimed by a lower-priority goal; that
        # is the meaning of the user's global priority ordering, and the lower
        # goal will rebuild its kit on a later planning cycle.
        if task.action == "Craft Item":
            recursive_items = self._recursive_item_requirements(task.target)
            for item_type, required in recursive_items.items():
                claims = item_claims.get(item_type, ())
                hard_floor = max((
                    amount for rank, amount in claims
                    if rank <= task_rank
                ), default=0)
                if hard_floor <= 0:
                    continue
                available = int(items.get(item_type, 0))
                if available - hard_floor < int(required):
                    conflicts.append("item_reserved_by_assembly_goal")
        return list(dict.fromkeys(conflicts))

    def _recursive_item_requirements(self, recipe_id):
        """Return physical item inputs the server could consume for one craft."""

        recipes = self.translator.operations.manufacturing.recipes
        required = {}

        def walk(current, multiplier, ancestors):
            if current in ancestors:
                return
            recipe = recipes.get(current)
            if recipe is None:
                return
            branch = ancestors | {current}
            for ingredient in recipe.get("ingredients", ()):
                kind = ingredient.get(
                    "kind",
                    "item" if ingredient.get("unit") == "item" else "resource",
                )
                if kind != "item":
                    continue
                item_type = ingredient.get("type")
                amount = int(ingredient.get("quantity", 0) or 0) * multiplier
                if not item_type or amount <= 0:
                    continue
                required[item_type] = required.get(item_type, 0) + amount
                walk(item_type, amount, branch)

        walk(recipe_id, 1, set())
        return required

    def _disposition(self, command, blockers, warnings):
        if blockers:
            return "blocked"

        if (
            not self.policy.live_execution_enabled
            or self.policy.mode == ExecutionMode.OBSERVE
        ):
            return "dry_run"

        if self.policy.mode == ExecutionMode.APPROVE:
            return "awaiting_approval"

        if any(
            warning.acknowledgement_recommended
            for warning in warnings
        ) and not command.metadata.get("routeRiskAcknowledged", False):
            return "awaiting_risk_acknowledgement"

        if (
            command.type not in self.policy.allowed_command_types
            and not command.metadata.get("workflowAuthorized", False)
        ):
            return "awaiting_approval"

        return "ready"
