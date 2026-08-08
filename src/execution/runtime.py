"""Policy-controlled, one-command automation runtime."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import sleep
from uuid import uuid4

from .commands import CommandType
from .policy import ExecutionMode
from .preflight import PreflightValidator


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    command: object
    response: object | None = None
    blockers: tuple[str, ...] = ()


class AutomationRuntime:
    """Refresh, revalidate, lease, dispatch, journal, and replan."""

    def __init__(
        self,
        *,
        capabilities,
        data_engine,
        policy,
        dispatcher,
        refresh,
        replan=None,
        lease_seconds=30,
        retry_attempts=1,
        cooldown_seconds=0,
        sleeper=sleep,
        owner=None,
    ):
        self.capabilities = capabilities
        self.data_engine = data_engine
        self.policy = policy
        self.dispatcher = dispatcher
        self.refresh = refresh
        self.replan = replan
        self.lease_seconds = lease_seconds
        self.retry_attempts = retry_attempts
        self.cooldown_seconds = cooldown_seconds
        self.sleeper = sleeper
        self.owner = owner or f"runtime-{uuid4()}"

    def execute(
        self,
        prepared,
        *,
        approved=False,
        risk_acknowledged=False,
        approval_expires_at=None,
    ):
        command = prepared.command
        self._record(command, "proposed", prepared.blockers)

        if prepared.blockers:
            return self._finish(command, "cancelled", prepared.blockers)
        if self.data_engine.emergency_stop_active():
            return self._finish(command, "cancelled", ("emergency_stop",))
        # Crafting and mining are repeatable goals. Once the previous task has
        # completed, an identical order from the same stable inventory state is
        # legitimate; the authoritative refresh and preflight below still stop
        # a duplicate while its Manny/printer is busy. Keep durable fingerprint
        # idempotency for one-time mutations such as movement and assembly.
        repeatable = command.type in {
            CommandType.MANNY_CRAFT,
            CommandType.ATOMIC_PRINTER_CRAFT,
            CommandType.MANNY_MINE,
        }
        if not repeatable and self.data_engine.action_was_successful(command.fingerprint):
            return self._finish(command, "cancelled", ("already_completed",))
        if not self.policy.live_execution_enabled:
            return self._finish(command, "cancelled", ("live_execution_disabled",))
        if self.policy.mode == ExecutionMode.OBSERVE:
            return self._finish(command, "cancelled", ("observe_only",))
        if command.type not in self.policy.allowed_command_types:
            return self._finish(command, "cancelled", ("command_not_allowlisted",))
        if self.policy.mode == ExecutionMode.APPROVE and not approved:
            return self._finish(command, "awaiting_approval")
        if approved and self._approval_expired(approval_expires_at):
            return self._finish(command, "expired", ("approval_expired",))
        if (
            any(
                warning.acknowledgement_recommended
                for warning in prepared.warnings
            )
            and not risk_acknowledged
        ):
            return self._finish(command, "awaiting_risk_acknowledgement")

        operations = self.refresh(command.probe_id)
        validator = PreflightValidator(operations, command.probe_id)
        blockers = validator.blockers(command)
        warnings = validator.warnings(command)
        if blockers:
            return self._finish(command, "cancelled", blockers)
        if (
            any(w.acknowledgement_recommended for w in warnings)
            and not risk_acknowledged
        ):
            return self._finish(command, "awaiting_risk_acknowledgement")

        expires_at = (
            datetime.now(UTC) + timedelta(seconds=self.lease_seconds)
        ).isoformat()
        if not self.data_engine.acquire_execution_lease(
            command.probe_id,
            command.fingerprint,
            self.owner,
            expires_at,
        ):
            return self._finish(command, "cancelled", ("execution_lease_unavailable",))

        self._record(command, "approved")
        self._record(command, "started")
        try:
            result = self._dispatch_with_retry(command)
        finally:
            self.data_engine.release_execution_lease(
                command.probe_id,
                command.fingerprint,
            )

        if self.replan is not None:
            self.replan(command.probe_id, result)
        return result

    def _dispatch_with_retry(self, command):
        for attempt in range(self.retry_attempts + 1):
            try:
                response = self.dispatcher.dispatch(command)
            except Exception as error:
                if attempt < self.retry_attempts and self._retryable(error):
                    self._record(command, "retrying", (type(error).__name__,))
                    delay = getattr(error, "retry_after", self.cooldown_seconds)
                    if delay > 0:
                        self.sleeper(delay)
                    continue
                self._record(command, "failed", (type(error).__name__,))
                return ExecutionResult(
                    "failed", command, response=self._error_response(error)
                )
            self._record(command, "succeeded")
            return ExecutionResult("succeeded", command, response=response)

    @staticmethod
    def _error_response(error):
        response = getattr(error, "response", None)
        detail = None
        if response is not None:
            try:
                detail = response.json()
            except (TypeError, ValueError):
                detail = getattr(response, "text", None)
        return {
            "error": str(error) or type(error).__name__,
            "detail": detail,
            "statusCode": getattr(response, "status_code", None),
        }

    @staticmethod
    def _retryable(error):
        status = getattr(error, "status_code", None)
        return isinstance(error, (TimeoutError, ConnectionError)) or status == 429 \
            or isinstance(status, int) and status >= 500

    @staticmethod
    def _approval_expired(expires_at):
        if expires_at is None:
            return False
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.now(UTC) >= expires_at

    def emergency_stop(self):
        self.data_engine.set_emergency_stop(True)

    def clear_emergency_stop(self):
        self.data_engine.set_emergency_stop(False)

    def _finish(self, command, status, blockers=()):
        self._record(command, status, blockers)
        return ExecutionResult(status, command, blockers=tuple(blockers))

    def _record(self, command, status, blockers=()):
        self.data_engine.record_action(
            command.fingerprint,
            command.to_dict(),
            status,
            blockers,
        )
