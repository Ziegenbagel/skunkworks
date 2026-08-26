"""Opt-in desktop-notification policy and restart-safe deduplication."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


POLICY_PREFERENCE = "desktop_notification_policy"
SEEN_PREFERENCE = "desktop_notification_seen"
DEFAULT_CATEGORIES = ("critical", "discoveries", "approvals", "operations", "failures")


@dataclass(frozen=True)
class NotificationCandidate:
    key: str
    category: str
    title: str
    message: str
    severity: str = "info"


def load_policy(preferences):
    try:
        stored = json.loads(preferences.get_preference(POLICY_PREFERENCE, "{}") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        stored = {}
    categories = stored.get("categories", DEFAULT_CATEGORIES)
    return {
        "enabled": bool(stored.get("enabled", False)),
        "categories": [item for item in DEFAULT_CATEGORIES if item in categories],
        "minimumSeverity": str(stored.get("minimumSeverity", "warning")) if str(stored.get("minimumSeverity", "warning")) in {"info", "warning", "critical"} else "warning",
    }


def save_policy(preferences, policy):
    value = {
        "enabled": bool(policy.get("enabled", False)),
        "categories": [item for item in DEFAULT_CATEGORIES if item in policy.get("categories", ())],
        "minimumSeverity": str(policy.get("minimumSeverity", "warning")) if str(policy.get("minimumSeverity", "warning")) in {"info", "warning", "critical"} else "warning",
    }
    preferences.set_preference(POLICY_PREFERENCE, json.dumps(value, sort_keys=True))
    return value


class NotificationCoordinator:
    """Extract new dashboard events without changing their viewed state."""

    def __init__(self, preferences, limit=512):
        self.preferences = preferences
        self.limit = max(32, int(limit))
        try:
            self.seen = list(json.loads(preferences.get_preference(SEEN_PREFERENCE, "[]") or "[]"))
        except (TypeError, ValueError, json.JSONDecodeError):
            self.seen = []
        self._seen = set(self.seen)

    @staticmethod
    def _key(prefix, *parts):
        content = "|".join(str(part or "") for part in parts)
        return prefix + ":" + hashlib.sha256(content.encode("utf-8")).hexdigest()[:24]

    def candidates(self, dashboard):
        result = []
        for alert in dashboard.get("alerts", ()):
            summary = str(alert.get("summary") or alert.get("message") or "Safety alert")
            severity = str(alert.get("severity") or alert.get("level") or "warning").lower()
            summary_lower = summary.lower()
            category = (
                "discoveries" if any(word in summary_lower for word in ("discover", "dormant construct", "blueprint"))
                else "failures" if "fail" in summary_lower
                else "critical"
            )
            result.append(NotificationCandidate(
                self._key("alert", alert.get("id"), alert.get("code"), summary),
                category, "Skunkworks safety alert", summary,
                "critical" if severity in {"critical", "danger", "error"} else "warning",
            ))
        last = dashboard.get("automationRuntime", {}).get("lastResult") or {}
        if last:
            succeeded = bool(last.get("accepted") or last.get("success"))
            category = "operations" if succeeded else "failures"
            message = str(last.get("message") or last.get("summary") or last.get("status") or "Automation cycle updated")
            result.append(NotificationCandidate(
                self._key("operation", last.get("fingerprint"), last.get("commandId"), message),
                category, "Skunkworks operation " + ("completed" if succeeded else "needs attention"), message,
                "info" if succeeded else "critical",
            ))
        for row in dashboard.get("automationRuntime", {}).get("queue", ()):
            disposition = str(row.get("disposition") or "").lower()
            if disposition in {"approval_required", "awaiting_approval", "ready_for_approval"}:
                message = str(row.get("summary") or row.get("displayText") or "An automation command awaits approval")
                result.append(NotificationCandidate(
                    self._key("approval", row.get("fingerprint"), message),
                    "approvals", "Skunkworks approval required", message,
                    "warning",
                ))
        return result

    def take_new(self, dashboard, policy=None, prime=False):
        policy = policy or load_policy(self.preferences)
        allowed = set(policy.get("categories", ()))
        ranks = {"info": 0, "warning": 1, "critical": 2}
        minimum = ranks.get(str(policy.get("minimumSeverity", "warning")), 1)
        candidates = self.candidates(dashboard)
        fresh = [] if prime or not policy.get("enabled") else [
            item for item in candidates
            if item.key not in self._seen and item.category in allowed
            and ranks.get(item.severity, 0) >= minimum
        ]
        for item in candidates:
            if item.key not in self._seen:
                self.seen.append(item.key)
                self._seen.add(item.key)
        self.seen = self.seen[-self.limit:]
        self._seen = set(self.seen)
        self.preferences.set_preference(SEEN_PREFERENCE, json.dumps(self.seen))
        return fresh
