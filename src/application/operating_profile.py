"""Persistent operating profiles for bounded background work."""

from __future__ import annotations

from dataclasses import asdict, dataclass


PROFILE_PREFERENCE = "operating_profile"


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
    "low_usage": OperatingProfile("low_usage", 2, 900, "reduced"),
}


def normalize_profile(value):
    return str(value or "normal").strip().lower() if str(value or "").strip().lower() in PROFILES else "normal"


def load_operating_profile(preferences):
    return PROFILES[normalize_profile(preferences.get_preference(PROFILE_PREFERENCE, "normal"))]


def save_operating_profile(preferences, value):
    name = normalize_profile(value)
    preferences.set_preference(PROFILE_PREFERENCE, name)
    return PROFILES[name]
