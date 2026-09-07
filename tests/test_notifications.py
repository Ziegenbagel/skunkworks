from src.application.notifications import NotificationCoordinator, save_policy
from src.ui.app import DesktopNotificationBridge
from src.ui.controller import MissionControlController


class ImmediatePool:
    @staticmethod
    def start(worker):
        worker.run()


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
    controller = MissionControlController(
        settings_engine=preferences, thread_pool=ImmediatePool(),
    )
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


def test_dashboard_notification_deduplication_is_deferred_off_ui_thread():
    workers = []

    class DeferredPool:
        @staticmethod
        def start(worker):
            workers.append(worker)

    preferences = Preferences()
    controller = MissionControlController(
        settings_engine=preferences, thread_pool=DeferredPool(),
    )

    controller._queue_notification_processing(
        {"alerts": [{"id": "a1", "summary": "Hull breach"}]},
        prime=True,
    )

    assert "desktop_notification_seen" not in preferences.values
    assert len(workers) == 1
    workers[0].run()
    assert "desktop_notification_seen" in preferences.values


def test_live_notification_result_reaches_controller_delivery_signal():
    preferences = Preferences()
    save_policy(preferences, {
        "enabled": True,
        "categories": ["operations"],
        "minimumSeverity": "info",
    })
    controller = MissionControlController(
        settings_engine=preferences, thread_pool=ImmediatePool(),
    )
    requested = []
    controller.desktopNotificationRequested.connect(
        lambda title, message: requested.append((title, message))
    )
    base = {
        "apiVersion": 128,
        "alerts": [],
        "focus": {"probeId": 7, "name": "Hub"},
        "probeOptions": [{"id": 7, "name": "Hub"}],
        "automationRuntime": {},
    }
    controller._accept_dashboard(dict(base))
    updated = dict(base)
    updated["automationRuntime"] = {
        "lastResult": {
            "accepted": True,
            "commandId": "command-1",
            "message": "Mining order accepted",
        },
    }

    controller._accept_dashboard(updated)

    assert requested == [
        ("Hub · Operation completed", "Mining order accepted")
    ]
    assert controller.dashboard["automationRuntime"]["lastResult"][
        "commandId"
    ] == "command-1"


def test_terminal_results_are_not_lost_while_notification_worker_is_busy():
    workers = []

    class DeferredPool:
        @staticmethod
        def start(worker):
            workers.append(worker)

    preferences = Preferences()
    save_policy(preferences, {
        "enabled": True, "categories": ["operations"],
        "minimumSeverity": "info",
    })
    controller = MissionControlController(
        settings_engine=preferences, thread_pool=DeferredPool(),
    )
    controller._notifications_primed = True
    controller._dashboard = {"focus": {"name": "Hub"}, "automationRuntime": {}}
    requested = []
    controller.desktopNotificationRequested.connect(
        lambda title, message: requested.append((title, message))
    )

    controller._queue_terminal_notification({
        "status": "succeeded", "commandType": "manny_mine",
        "commandId": "one",
    })
    controller._queue_terminal_notification({
        "status": "succeeded", "commandType": "manny_craft",
        "commandId": "two",
    })

    assert len(workers) == 1
    workers.pop(0).run()
    assert len(workers) == 1
    workers.pop(0).run()
    assert [title for title, _message in requested] == [
        "Hub · Manny Mine completed", "Hub · Manny Craft completed",
    ]


def test_manual_acceptance_enters_notification_path_without_waiting_for_refresh():
    preferences = Preferences()
    save_policy(preferences, {
        "enabled": True, "categories": ["operations"],
        "minimumSeverity": "info",
    })
    controller = MissionControlController(
        settings_engine=preferences, thread_pool=ImmediatePool(),
    )
    controller._notifications_primed = True
    controller._dashboard = {"focus": {"name": "Hub"}, "automationRuntime": {}}
    requested = []
    controller.desktopNotificationRequested.connect(
        lambda title, message: requested.append((title, message))
    )

    controller._command_accepted(
        {"commandId": "manual-1", "commandType": "move_probe"},
        "TRAVEL ORDER ACCEPTED · SYNCING", refresh=False,
    )

    assert requested == [
        ("Hub · Move Probe completed", "TRAVEL ORDER ACCEPTED · SYNCING")
    ]


def test_repeated_manual_acceptances_without_server_ids_remain_distinct():
    preferences = Preferences()
    save_policy(preferences, {
        "enabled": True, "categories": ["operations"],
        "minimumSeverity": "info",
    })
    controller = MissionControlController(
        settings_engine=preferences, thread_pool=ImmediatePool(),
    )
    controller._notifications_primed = True
    controller._dashboard = {"focus": {"name": "Hub"}, "automationRuntime": {}}
    requested = []
    controller.desktopNotificationRequested.connect(
        lambda title, message: requested.append((title, message))
    )

    controller._command_accepted({}, "ORDER ACCEPTED · SYNCING", refresh=False)
    controller._command_accepted({}, "ORDER ACCEPTED · SYNCING", refresh=False)

    assert len(requested) == 2


def test_failed_manual_command_enters_failure_notification_path():
    preferences = Preferences()
    save_policy(preferences, {
        "enabled": True, "categories": ["failures"],
        "minimumSeverity": "warning",
    })
    controller = MissionControlController(
        settings_engine=preferences, thread_pool=ImmediatePool(),
    )
    controller._notifications_primed = True
    controller._dashboard = {"focus": {"name": "Hub"}, "automationRuntime": {}}
    requested = []
    controller.desktopNotificationRequested.connect(
        lambda title, message: requested.append((title, message))
    )

    controller._queue_command_failure_notification(
        "Insufficient fuel", command_type="move_probe",
    )

    assert requested == [
        ("Hub · Move Probe needs attention", "Insufficient fuel")
    ]


def test_desktop_notification_bridge_owns_tray_delivery_slot():
    calls = []

    class TrayIcon:
        @staticmethod
        def showMessage(title, message, icon, timeout):
            calls.append((title, message, icon, timeout))

    bridge = DesktopNotificationBridge(TrayIcon())
    bridge.deliver("Safety alert", "Hull breach")

    assert calls[0][0:2] == ("Safety alert", "Hull breach")
    assert calls[0][3] == 8000


def test_desktop_notification_is_suppressed_while_window_is_active():
    calls = []

    class TrayIcon:
        @staticmethod
        def showMessage(*args):
            calls.append(args)

    bridge = DesktopNotificationBridge(TrayIcon(), should_deliver=lambda: False)
    bridge.deliver("Hub · Manny craft completed", "Manny craft succeeded.")

    assert calls == []


def test_status_only_success_uses_operation_and_probe_instead_of_failure_copy():
    dashboard = {
        "focus": {"name": "Ziegenbagel Skunkworks Hub"},
        "automationRuntime": {"lastResult": {
            "status": "succeeded",
            "commandType": "manny_craft",
            "fingerprint": "craft-1",
        }},
    }

    candidates = NotificationCoordinator(Preferences()).candidates(dashboard)

    assert [(item.category, item.title, item.message) for item in candidates] == [
        (
            "operations",
            "Ziegenbagel Skunkworks Hub · Manny Craft completed",
            "Manny Craft succeeded.",
        )
    ]


def test_unidentified_bare_status_does_not_create_vague_notification():
    dashboard = {"automationRuntime": {"lastResult": {"status": "succeeded"}}}

    assert NotificationCoordinator(Preferences()).candidates(dashboard) == []
