import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: window
    property var backend: null
    width: Constants.width
    height: Constants.height
    minimumWidth: Constants.minimumWidth
    minimumHeight: Constants.minimumHeight
    visible: true
    title: "Skunkworks Mission Control"
    color: Constants.voidColor

    Component.onCompleted: AudioManager.startMusic()

    MissionControlScreen {
        id: missionControl
        anchors.fill: parent
        liveMode: window.backend !== null
        dashboardData: window.backend ? window.backend.dashboard : ({})
        availableProbes: window.backend && window.backend.availableProbes.length ? window.backend.availableProbes : previewProbes
        focusedProbeId: window.backend && window.backend.focusedProbeId >= 0 ? window.backend.focusedProbeId : availableProbes[0].id
        refreshing: window.backend ? window.backend.refreshing : false
        connectionError: window.backend ? window.backend.error : ""
        emergencyStopActive: window.backend ? window.backend.emergencyStopActive : false
        visible: !startupOverlay.visible
    }

    Rectangle {
        id: startupOverlay
        anchors.fill: parent
        z: 900
        visible: window.backend !== null && window.backend.startupLoading
        color: Constants.voidColor

        Column {
            anchors.centerIn: parent
            spacing: 22

            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "S K U N K W O R K S"
                color: Constants.textColor
                font.family: Constants.displayFont
                font.pixelSize: 38
                font.bold: true
            }
            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "AUTONOMOUS EXPLORATION & FLEET OPERATIONS"
                color: Constants.cyanColor
                font.family: Constants.technicalFont
                font.pixelSize: 14
                font.letterSpacing: 2
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 360
                height: 2
                color: Constants.lineColor
                Rectangle {
                    id: loadingSweep
                    width: 90
                    height: parent.height
                    color: Constants.cyanColor
                    SequentialAnimation on x {
                        loops: Animation.Infinite
                        NumberAnimation { from: 0; to: 270; duration: 900; easing.type: Easing.InOutQuad }
                        NumberAnimation { from: 270; to: 0; duration: 900; easing.type: Easing.InOutQuad }
                    }
                }
            }
            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "ESTABLISHING SECURE LINK · LOADING LIVE FLEET DATA"
                color: Constants.mutedTextColor
                font.family: Constants.technicalFont
                font.pixelSize: 12
            }
        }
    }

    FirstLaunchWizard {
        id: firstLaunchWizard
        anchors.fill: parent
        z: 1000
        visible: window.backend ? window.backend.onboardingRequired : false
        credentialConfigured: window.backend ? window.backend.credentialConfigured : false
        credentialMessage: window.backend ? window.backend.credentialMessage : ""
        onApiKeySaveRequested: apiKey => { if (window.backend) window.backend.saveApiKey(apiKey); }
        onApiKeyTestRequested: { if (window.backend) window.backend.testApiKey(); }
        onFinishRequested: { if (window.backend) window.backend.completeOnboarding(); }
    }

    Connections {
        target: window.backend
        ignoreUnknownSignals: true

        function onStartupLoadingChanged() {
            if (window.backend && !window.backend.startupLoading)
                AudioManager.play("load");
        }
        function onErrorChanged() {
            if (window.backend && window.backend.error)
                AudioManager.play("error");
        }
    }

    Connections {
        target: missionControl.probeSelectorControl

        function onProbeSelected(probeId) {
            AudioManager.play("select");
            if (window.backend)
                window.backend.selectProbe(probeId);
            else
                missionControl.focusedProbeId = probeId;
        }

        function onRefreshRequested() {
            AudioManager.play("press");
            if (window.backend)
                window.backend.refresh();
        }
    }

    Connections {
        target: missionControl.emergencyStopControl

        function onClicked() {
            AudioManager.play(window.backend && window.backend.emergencyStopActive ? "confirm" : "warning");
            if (window.backend)
                window.backend.setEmergencyStop(!window.backend.emergencyStopActive);
        }
    }

    Connections {
        target: missionControl.alertsButtonControl

        function onClicked() {
            AudioManager.play("navigate");
            missionControl.currentNavigation = "SAFETY";
        }
    }

    Connections {
        target: missionControl.navigationBarControl

        function onSectionSelected(section) {
            AudioManager.play("navigate");
            missionControl.currentNavigation = section;
        }
    }

    Connections {
        target: missionControl.navigationWorkspaceControl

        function onProbeSelected(probeId) {
            AudioManager.play("select");
            if (window.backend)
                window.backend.selectProbe(probeId);
            else
                missionControl.focusedProbeId = probeId;
        }

        function onAutomationSettingsSaved(settings) {
            AudioManager.play("save");
            if (window.backend)
                window.backend.saveAutomationSettings(settings);
        }

        function onProbeRoleAssigned(probeId, role) {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.assignProbeRole(probeId, role);
        }

        function onTravelPreviewRequested(x, y, z, routeMode) {
            AudioManager.play("press");
            if (window.backend)
                window.backend.previewTravel(x, y, z, routeMode);
        }

        function onTravelExecuteRequested(riskAcknowledged) {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.executeTravel(riskAcknowledged);
        }

        function onSectorScanRequested(x, y, z) {
            AudioManager.play("press");
            if (window.backend)
                window.backend.scanSector(x, y, z);
        }

        function onNeighboringSectorsScanRequested() {
            AudioManager.play("press");
            if (window.backend)
                window.backend.scanNeighboringSectors();
        }

        function onAutonomousTravelTargetRequested(x, y, z) {
            AudioManager.play("save");
            if (window.backend)
                window.backend.setAutonomousTravelTarget(x, y, z);
        }

        function onApiKeySaveRequested(apiKey) {
            AudioManager.play("save");
            if (window.backend) window.backend.saveApiKey(apiKey);
        }

        function onApiKeyTestRequested() {
            AudioManager.play("press");
            if (window.backend) window.backend.testApiKey();
        }

        function onApiKeyRemoveRequested() {
            AudioManager.play("warning");
            if (window.backend) window.backend.removeApiKey();
        }

        function onOnboardingResetRequested() {
            AudioManager.play("press");
            if (window.backend) window.backend.resetOnboarding();
        }

        function onExecutionPolicySaveRequested(policy) {
            AudioManager.play("save");
            if (window.backend) window.backend.saveExecutionPolicy(policy);
        }

        function onAutomationCycleRequested() {
            AudioManager.play("confirm");
            if (window.backend) window.backend.runAutomationCycle();
        }

        function onAutomationApprovalRequested(fingerprint, riskAcknowledged) {
            AudioManager.play("confirm");
            if (window.backend) window.backend.approveAutomationCommand(fingerprint, riskAcknowledged);
        }

        function onTransportCycleSaveRequested(plan) {
            AudioManager.play("save");
            if (window.backend) window.backend.saveTransportCycle(plan);
        }

        function onProbeRenameRequested(name) {
            AudioManager.play("save");
            if (window.backend) window.backend.renameFocusedProbe(name);
        }

        function onContainerRenameRequested(containerId, label) {
            AudioManager.play("save");
            if (window.backend) window.backend.renameStorageContainer(containerId, label);
        }

        function onStorageRulesSaveRequested(containerId, rules) {
            AudioManager.play("save");
            if (window.backend) window.backend.saveStorageRules(containerId, rules);
        }

        function onStorageMoveRequested(payload) {
            AudioManager.play("confirm");
            if (window.backend) window.backend.moveStorage(payload);
        }

        function onJettisonRequested(itemId, amount, containerId) {
            AudioManager.play("warning");
            if (window.backend) window.backend.jettisonInventory(itemId, amount, containerId);
        }

        function onInventoryMannyActionRequested(action, mannyId, payload) {
            AudioManager.play(action === "transfer-deuterium-to-probe" ? "confirm" : "warning");
            if (window.backend) window.backend.runInventoryMannyAction(action, mannyId, payload);
        }

        function onLogbookCreateRequested(title, content) {
            AudioManager.play("save");
            if (window.backend) window.backend.createLogbookPage(title, content);
        }

        function onLogbookUpdateRequested(pageId, title, content) {
            AudioManager.play("save");
            if (window.backend) window.backend.updateLogbookPage(pageId, title, content);
        }

        function onLogbookDeleteRequested(pageId) {
            AudioManager.play("warning");
            if (window.backend) window.backend.deleteLogbookPage(pageId);
        }

        function onAutoLogbookChanged(enabled) {
            AudioManager.play("press");
            if (window.backend) window.backend.setAutoLogbookEnabled(enabled);
        }

        function onLogbookPageOpenRequested(pageId) {
            AudioManager.play("select");
            if (window.backend) window.backend.loadLogbookPage(pageId);
        }

        function onOperatorManualRequested() {
            AudioManager.play("navigate");
            if (window.backend) window.backend.openOperatorManual();
        }

        function onChangeLogRequested() {
            AudioManager.play("navigate");
            if (window.backend) window.backend.openChangeLog();
        }

        function onUpdateCheckRequested() {
            AudioManager.play("navigate");
            if (window.backend) window.backend.checkForUpdates();
        }
    }
}
