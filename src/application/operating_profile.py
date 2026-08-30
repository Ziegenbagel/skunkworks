"""Persistent operating profiles for bounded background work."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json


PROFILE_PREFERENCE = "operating_profile"
PROFILE_IDLE_MINUTES_PREFERENCE = "operating_profile_idle_minutes"
PROFILE_SCHEDULE_PREFERENCE = "operating_profile_schedule"
DEFAULT_IDLE_MINUTES = 10
MINIMUM_IDLE_MINUTES = 1
MAXIMUM_IDLE_MINUTES = 120


@dataclass(frozen=True)
class OperatingProfile:
    name: str
    background_probes_per_cycle: int
    archival_sync_seconds: int
    map_detail: str

    def payload(self):
        return asdict(self)


PROFILES = {
    "normal": OperatingProfile("normal", 4, 300, "normal"),
    "low_usage": OperatingProfile("low_usage", 1, 1800, "reduced"),
    # Auto is a persisted selection, not an execution profile. The controller
    # resolves it to Normal while the operator is active and Low Power after
    # the configured idle interval.
    "auto": OperatingProfile("auto", 4, 300, "normal"),
    # Scheduled is also a persisted selection. Its effective behavior is
    # resolved against local wall-clock time by the controller.
    "scheduled": OperatingProfile("scheduled", 4, 300, "normal"),
}


def normalize_profile(value):
    return str(value or "normal").strip().lower() if str(value or "").strip().lower() in PROFILES else "normal"


def load_operating_profile(preferences):
    return PROFILES[normalize_profile(preferences.get_preference(PROFILE_PREFERENCE, "normal"))]


def save_operating_profile(preferences, value):
    name = normalize_profile(value)
    preferences.set_preference(PROFILE_PREFERENCE, name)
    return PROFILES[name]


def normalize_idle_minutes(value):
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        minutes = DEFAULT_IDLE_MINUTES
    return max(MINIMUM_IDLE_MINUTES, min(MAXIMUM_IDLE_MINUTES, minutes))


def load_operating_profile_idle_minutes(preferences):
    return normalize_idle_minutes(
        preferences.get_preference(
            PROFILE_IDLE_MINUTES_PREFERENCE, str(DEFAULT_IDLE_MINUTES),
        )
    )


def save_operating_profile_idle_minutes(preferences, value):
    minutes = normalize_idle_minutes(value)
    preferences.set_preference(PROFILE_IDLE_MINUTES_PREFERENCE, str(minutes))
    return minutes


def _normalized_time(value, fallback):
    text = str(value or fallback).strip()
    try:
        hour, minute = (int(part) for part in text.split(":"))
    except (TypeError, ValueError):
        return fallback
    return f"{hour:02d}:{minute:02d}" if 0 <= hour <= 23 and 0 <= minute <= 59 else fallback


def normalize_operating_profile_schedule(value, now=None):
    value = dict(value or {})
    start = _normalized_time(value.get("start_time"), "22:00")
    end = _normalized_time(value.get("end_time"), "07:00")
    recurrence = "once" if str(value.get("recurrence")) == "once" else "daily"
    schedule = {"start_time": start, "end_time": end, "recurrence": recurrence}
    if recurrence == "once":
        current = now or datetime.now().astimezone()
        start_hour, start_minute = (int(part) for part in start.split(":"))
        end_hour, end_minute = (int(part) for part in end.split(":"))
        starts_at = current.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        if starts_at <= current:
            starts_at += timedelta(days=1)
        ends_at = starts_at.replace(hour=end_hour, minute=end_minute)
        if ends_at <= starts_at:
            ends_at += timedelta(days=1)
        schedule.update({"starts_at": starts_at.timestamp(), "ends_at": ends_at.timestamp()})
    return schedule


def load_operating_profile_schedule(preferences):
    raw = preferences.get_preference(PROFILE_SCHEDULE_PREFERENCE, "{}")
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        value = {}
    # Preserve persisted one-time epochs rather than moving a saved schedule.
    normalized = normalize_operating_profile_schedule(value)
    if normalized["recurrence"] == "once" and isinstance(value, dict):
        for key in ("starts_at", "ends_at"):
            if key in value:
                normalized[key] = float(value[key])
    return normalized


def save_operating_profile_schedule(preferences, value, now=None):
    schedule = normalize_operating_profile_schedule(value, now=now)
    preferences.set_preference(PROFILE_SCHEDULE_PREFERENCE, json.dumps(schedule))
    return schedule


def resolve_scheduled_operating_profile(schedule, now=None):
    current = now or datetime.now().astimezone()
    if schedule.get("recurrence") == "once":
        timestamp = current.timestamp()
        active = float(schedule.get("starts_at", 0)) <= timestamp < float(schedule.get("ends_at", 0))
        status = "active" if active else ("completed" if timestamp >= float(schedule.get("ends_at", 0)) else "upcoming")
    else:
        current_minute = current.hour * 60 + current.minute
        start_hour, start_minute = (int(part) for part in schedule["start_time"].split(":"))
        end_hour, end_minute = (int(part) for part in schedule["end_time"].split(":"))
        start = start_hour * 60 + start_minute
        end = end_hour * 60 + end_minute
        active = start <= current_minute < end if start < end else current_minute >= start or current_minute < end
        status = "active" if active else "waiting"
    return PROFILES["low_usage"] if active else PROFILES["normal"], status


def resolve_effective_operating_profile(selected_profile, idle_seconds, idle_minutes):
    """Resolve a persisted selection into the profile currently being applied."""
    if selected_profile.name != "auto":
        return selected_profile
    threshold_seconds = normalize_idle_minutes(idle_minutes) * 60
    return (
        PROFILES["low_usage"]
        if max(0.0, float(idle_seconds)) >= threshold_seconds
        else PROFILES["normal"]
    )
