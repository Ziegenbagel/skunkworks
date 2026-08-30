from src.application.operating_profile import (
    load_operating_profile,
    load_operating_profile_idle_minutes,
    resolve_effective_operating_profile,
    save_operating_profile,
    save_operating_profile_idle_minutes,
    save_operating_profile_schedule,
    load_operating_profile_schedule,
    resolve_scheduled_operating_profile,
)
from datetime import datetime


class Preferences:
    def __init__(self): self.values = {}
    def get_preference(self, key, default=None): return self.values.get(key, default)
    def set_preference(self, key, value): self.values[key] = value


def test_low_usage_reduces_only_background_work():
    preferences = Preferences()
    profile = save_operating_profile(preferences, "low_usage")
    assert profile.background_probes_per_cycle == 1
    assert profile.archival_sync_seconds == 1800
    assert profile.map_detail == "reduced"
    assert load_operating_profile(preferences) == profile


def test_unknown_profile_falls_back_to_normal():
    preferences = Preferences()
    preferences.values["operating_profile"] = "future-mode"
    assert load_operating_profile(preferences).name == "normal"


def test_auto_profile_and_idle_timeout_are_persistent_and_bounded():
    preferences = Preferences()
    assert save_operating_profile(preferences, "auto").name == "auto"
    assert save_operating_profile_idle_minutes(preferences, 0) == 1
    assert load_operating_profile_idle_minutes(preferences) == 1
    assert save_operating_profile_idle_minutes(preferences, 999) == 120
    assert load_operating_profile_idle_minutes(preferences) == 120


def test_auto_profile_enters_low_power_only_at_the_idle_threshold():
    selected = save_operating_profile(Preferences(), "auto")
    assert resolve_effective_operating_profile(selected, 599, 10).name == "normal"
    assert resolve_effective_operating_profile(selected, 600, 10).name == "low_usage"
    assert resolve_effective_operating_profile(selected, 0, 10).name == "normal"


def test_daily_schedule_supports_an_overnight_low_power_window():
    preferences = Preferences()
    schedule = save_operating_profile_schedule(
        preferences,
        {"start_time": "22:00", "end_time": "07:00", "recurrence": "daily"},
    )

    assert load_operating_profile_schedule(preferences) == schedule
    assert resolve_scheduled_operating_profile(
        schedule, datetime.fromisoformat("2026-08-30T23:00:00-07:00"),
    )[0].name == "low_usage"
    assert resolve_scheduled_operating_profile(
        schedule, datetime.fromisoformat("2026-08-30T12:00:00-07:00"),
    )[0].name == "normal"


def test_once_schedule_uses_the_next_start_and_then_completes():
    preferences = Preferences()
    now = datetime.fromisoformat("2026-08-30T20:00:00-07:00")
    schedule = save_operating_profile_schedule(
        preferences,
        {"start_time": "22:00", "end_time": "23:00", "recurrence": "once"},
        now=now,
    )

    active, status = resolve_scheduled_operating_profile(
        schedule, datetime.fromisoformat("2026-08-30T22:30:00-07:00"),
    )
    completed, completed_status = resolve_scheduled_operating_profile(
        schedule, datetime.fromisoformat("2026-08-30T23:30:00-07:00"),
    )
    assert (active.name, status) == ("low_usage", "active")
    assert (completed.name, completed_status) == ("normal", "completed")
