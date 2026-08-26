from src.application.operating_profile import load_operating_profile, save_operating_profile


class Preferences:
    def __init__(self): self.values = {}
    def get_preference(self, key, default=None): return self.values.get(key, default)
    def set_preference(self, key, value): self.values[key] = value


def test_low_usage_reduces_only_background_work():
    preferences = Preferences()
    profile = save_operating_profile(preferences, "low_usage")
    assert profile.background_probes_per_cycle == 1
    assert profile.archival_sync_seconds == 900
    assert profile.map_detail == "reduced"
    assert load_operating_profile(preferences) == profile


def test_unknown_profile_falls_back_to_normal():
    preferences = Preferences()
    preferences.values["operating_profile"] = "future-mode"
    assert load_operating_profile(preferences).name == "normal"
