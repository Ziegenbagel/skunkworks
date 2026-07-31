"""UI-independent refresh scheduling and mutation invalidation."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class RefreshRequest:
    domain: str
    probe_id: int | None
    due_at: datetime
    priority: int
    reason: str


class RefreshScheduler:
    def __init__(self, *, focused_probe_id=None, now=None):
        self.focused_probe_id = focused_probe_id
        self._now = now or (lambda: datetime.now(UTC))
        self._requests = {}

    def schedule(
        self, domain, *, probe_id=None,
        next_useful_refresh_delay_ms=30000, reason="api_hint",
    ):
        priority = 100 if probe_id == self.focused_probe_id else 50
        due = self._now() + timedelta(milliseconds=max(0, next_useful_refresh_delay_ms))
        request = RefreshRequest(domain, probe_id, due, priority, reason)
        self._requests[(domain, probe_id)] = request
        return request

    def invalidate_after_mutation(self, probe_id, domains=("probe", "sector", "mannies")):
        return tuple(
            self._set_immediate(domain, probe_id, "mutation") for domain in domains
        )

    def due(self, at=None):
        at = at or self._now()
        return tuple(
            sorted(
                (request for request in self._requests.values() if request.due_at <= at),
                key=lambda request: (-request.priority, request.due_at),
            )
        )

    def completed(self, request, next_useful_refresh_delay_ms=30000):
        return self.schedule(
            request.domain, probe_id=request.probe_id,
            next_useful_refresh_delay_ms=next_useful_refresh_delay_ms,
        )

    def _set_immediate(self, domain, probe_id, reason):
        priority = 110 if probe_id == self.focused_probe_id else 90
        request = RefreshRequest(domain, probe_id, self._now(), priority, reason)
        self._requests[(domain, probe_id)] = request
        return request
