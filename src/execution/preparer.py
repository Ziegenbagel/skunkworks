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

        for task in tasks:
            command = self.translator.translate(task)

            if command is None:
                continue

            blockers = list(self.validator.blockers(command))
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
