from src.application.notifications import NotificationCoordinator, save_policy


class Preferences:
    def __init__(self): self.values = {}
    def get_preference(self, key, default=None): return self.values.get(key, default)
    def set_preference(self, key, value): self.values[key] = value


def test_notifications_are_opt_in_and_deduplicated_across_restart():
    preferences = Preferences()
    dashboard = {"alerts": [{"id": "a1", "severity": "critical", "summary": "Hull breach"}]}
    coordinator = NotificationCoordinator(preferences)
    assert coordinator.take_new(dashboard) == []
    policy = save_policy(preferences, {"enabled": True, "categories": ["critical"], "minimumSeverity": "warning"})
    assert coordinator.take_new(dashboard, policy, prime=True) == []
    dashboard["alerts"].append({"id": "a2", "severity": "critical", "summary": "Fuel critical"})
    assert [item.message for item in coordinator.take_new(dashboard, policy)] == ["Fuel critical"]
    assert NotificationCoordinator(preferences).take_new(dashboard, policy) == []


def test_discoveries_and_approvals_respect_category_controls():
    preferences = Preferences()
    policy = save_policy(preferences, {"enabled": True, "categories": ["discoveries", "approvals"], "minimumSeverity": "info"})
    dashboard = {
        "alerts": [{"id": "d1", "summary": "Dormant construct discovered"}],
        "automationRuntime": {"queue": [{"fingerprint": "p1", "disposition": "approval_required", "summary": "Launch route awaits approval"}]},
    }
    fresh = NotificationCoordinator(preferences).take_new(dashboard, policy)
    assert {item.category for item in fresh} == {"discoveries", "approvals"}
