"""Persistent operating profiles for bounded background work."""

from __future__ import annotations

from dataclasses import asdict, dataclass


PROFILE_PREFERENCE = "operating_profile"
PROFILE_IDLE_MINUTES_PREFERENCE = "operating_profile_idle_minutes"
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
