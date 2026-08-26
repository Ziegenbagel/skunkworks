from src.application.notifications import NotificationCoordinator, save_policy
from src.ui.controller import MissionControlController


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


def test_test_notification_requires_saved_policy_and_supported_delivery():
    preferences = Preferences()
    controller = MissionControlController(settings_engine=preferences)
    requested = []
    controller.desktopNotificationRequested.connect(
        lambda title, message: requested.append((title, message))
    )

    controller.configureNotificationDelivery(True, True, "SUPPORTED")
    controller.sendTestNotification()
    assert requested == []

    controller.saveNotificationPolicy(
        {"enabled": True, "categories": ["critical"], "minimumSeverity": "warning"}
    )
    controller.sendTestNotification()
    assert requested == [
        (
            "Skunkworks test notification",
            "Desktop notification delivery was requested successfully.",
        )
    ]
    assert "REQUESTED" in controller.operationNotice
