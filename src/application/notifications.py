"""Opt-in desktop-notification policy and restart-safe deduplication."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


POLICY_PREFERENCE = "desktop_notification_policy"
SEEN_PREFERENCE = "desktop_notification_seen"
DEFAULT_CATEGORIES = ("critical", "discoveries", "approvals", "operations", "failures")
SUCCESS_STATUSES = {"accepted", "completed", "success", "succeeded"}
FAILURE_STATUSES = {"cancelled", "failed", "rejected"}


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

    @staticmethod
    def _operation_label(result):
        command_type = str(result.get("commandType") or "").strip()
        if not command_type:
            command_types = {
                str(item.get("commandType") or "").strip()
                for item in result.get("results", ())
                if isinstance(item, dict) and item.get("commandType")
            }
            if len(command_types) == 1:
                command_type = command_types.pop()
            elif command_types:
                return "Automation cycle"
        return command_type.replace("_", " ").strip().title()

    @staticmethod
    def _probe_label(dashboard):
        focus = dashboard.get("focus") or {}
        return str(focus.get("name") or "").strip()

    @staticmethod
    def _specific_message(result, status, operation):
        message = str(result.get("message") or result.get("summary") or "").strip()
        generic = {
            "accepted", "completed", "failed", "rejected", "success",
            "succeeded", status.replace("_", " "),
        }
        if message and message.lower().rstrip(".") not in generic:
            return message
        if operation:
            outcome = "succeeded" if status in SUCCESS_STATUSES else status.replace("_", " ")
            return f"{operation} {outcome}."
        return ""

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
            status = str(last.get("status") or "").strip().lower()
            succeeded = bool(last.get("accepted") or last.get("success")) or status in SUCCESS_STATUSES
            failed = status in FAILURE_STATUSES
            operation = self._operation_label(last)
            message = self._specific_message(last, status, operation)
            # Idle/observe/approval states are represented elsewhere. A bare
            # terminal status without an identifiable operation is not useful
            # enough to interrupt the operator.
            if (succeeded or failed) and message:
                probe = self._probe_label(dashboard)
                subject = operation or "Operation"
                title = " · ".join(item for item in (probe, subject) if item)
                title += " completed" if succeeded else " needs attention"
                category = "operations" if succeeded else "failures"
                result.append(NotificationCandidate(
                    self._key(
                        "operation", last.get("fingerprint"),
                        last.get("commandId"), last.get("notificationEventId"),
                        status, subject, message,
                    ),
                    category, title, message,
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
