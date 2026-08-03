"""Prepare, classify, and journal commands without executing them."""

from dataclasses import dataclass

from .policy import ExecutionMode
from .preflight import PreflightValidator
from .translator import TaskCommandTranslator


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
        prepared = []
        resource_claims = {}
        item_claims = self._goal_item_claims(tasks)
        background_mining_slots = self._background_mining_slots()

        for task in tasks:
            if (
                task.category == "mining"
                and getattr(task, "background_work", False)
                and background_mining_slots <= 0
            ):
                continue
            reservation_blockers = self._reserve_manufacturing_inputs(
                task, resource_claims, item_claims,
            )
            command = self.translator.translate(task)

            if command is None:
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

            if (
                not blockers
                and task.category == "mining"
                and getattr(task, "background_work", False)
            ):
                background_mining_slots -= 1

            if self.journal is not None:
                self.journal.record(
                    command,
                    disposition,
                    blockers,
                )

        return tuple(
            prepared[: self.policy.max_commands_per_cycle]
        )

    def _background_mining_slots(self):
        """Keep reserve-floor mining from saturating the Manny workforce.

        Production-dependency mining remains unrestricted. Pure stockpile
        replenishment may use at most one third of the onboard workforce, with
        a minimum of one worker for small probes.
        """

        mannies = self.translator.operations.world.mannies.get("mannies", ())
        onboard = [
            manny for manny in mannies
            if (manny.get("location") or {}).get("type") == "probe"
        ]
        workforce = len(onboard)
        if workforce == 0:
            return 0
        budget = max(1, workforce // 3)
        active_background_candidates = 0
        for manny in mannies:
            current = manny.get("currentTask")
            details = current if isinstance(current, dict) else manny.get("task") or {}
            task_type = details.get("type") if isinstance(current, dict) else current
            if task_type == "mining":
                active_background_candidates += 1
        return max(0, budget - active_background_candidates)

    @staticmethod
    def _goal_item_claims(tasks):
        """Seed claims for completed parts committed to assembly goals.

        Every task emitted for the same goal carries the same snapshot, so use
        the maximum claim at each priority rather than adding duplicate copies.
        """

        grouped = {}
        for task in tasks:
            for item_type, amount in getattr(task, "reserved_items", ()):
                key = (item_type, task.priority)
                grouped[key] = max(grouped.get(key, 0), int(amount))
        claims = {}
        for (item_type, priority), amount in grouped.items():
            claims.setdefault(item_type, []).append((priority, amount))
        return claims

    def _reserve_manufacturing_inputs(self, task, resource_claims, item_claims):
        if task.action not in {"Craft Item", "Prepare Manufacturing"} or not task.target:
            return []
        # The dispatcher starts one craft per proposal. Reserve the inputs for
        # the next unit of a higher-priority goal, not its entire desired batch;
        # otherwise a large long-term target can strand usable surplus and idle
        # fabricators while protected work is already in progress.
        plan = self.translator.operations.manufacturing.production_plan(
            task.target,
            quantity=1,
            include_operational_constraints=False,
        )
        if plan is None:
            return []
        resources, items = self.translator.operations.manufacturing.available_inputs()
        conflicts = []
        for resource, required in plan["required_resources"].items():
            available = float(resources.get(resource, 0))
            claims = resource_claims.setdefault(resource, [])
            higher_claimed = sum(
                amount for priority, amount in claims
                if priority < task.priority
            )
            available_after_higher = max(0, available - higher_claimed)
            if (
                task.action == "Craft Item"
                and available_after_higher + 0.00001 < float(required)
            ):
                conflicts.append("resource_reserved_by_higher_priority_goal")
            claims.append((task.priority, min(float(required), available)))
        for item_type, required in plan["consumed_inventory_items"].items():
            available = int(items.get(item_type, 0))
            claims = item_claims.setdefault(item_type, [])
            higher_claimed = sum(
                amount for priority, amount in claims
                if priority < task.priority
            )
            available_after_higher = max(0, available - higher_claimed)
            if task.action == "Craft Item" and available_after_higher < int(required):
                conflicts.append("item_reserved_by_higher_priority_goal")
            claims.append((task.priority, min(int(required), available)))
        return list(dict.fromkeys(conflicts))

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
        ):
            return "awaiting_risk_acknowledgement"

        if (
            command.type
            not in self.policy.allowed_command_types
        ):
            return "awaiting_approval"

        return "ready"
