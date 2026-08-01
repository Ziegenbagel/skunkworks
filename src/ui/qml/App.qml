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
        target: missionControl.probeSelectorControl

        function onProbeSelected(probeId) {
            if (window.backend)
                window.backend.selectProbe(probeId);
            else
                missionControl.focusedProbeId = probeId;
        }

        function onRefreshRequested() {
            if (window.backend)
                window.backend.refresh();
        }
    }

    Connections {
        target: missionControl.emergencyStopControl

        function onClicked() {
            if (window.backend)
                window.backend.setEmergencyStop(!window.backend.emergencyStopActive);
        }
    }

    Connections {
        target: missionControl.alertsButtonControl

        function onClicked() {
            missionControl.currentNavigation = "SAFETY";
        }
    }

    Connections {
        target: missionControl.navigationBarControl

        function onSectionSelected(section) {
            missionControl.currentNavigation = section;
        }
    }

    Connections {
        target: missionControl.navigationWorkspaceControl

        function onProbeSelected(probeId) {
            if (window.backend)
                window.backend.selectProbe(probeId);
            else
                missionControl.focusedProbeId = probeId;
        }

        function onAutomationSettingsSaved(settings) {
            if (window.backend)
                window.backend.saveAutomationSettings(settings);
        }

        function onProbeRoleAssigned(probeId, role) {
            if (window.backend)
                window.backend.assignProbeRole(probeId, role);
        }

        function onTravelPreviewRequested(x, y, z, routeMode) {
            if (window.backend)
                window.backend.previewTravel(x, y, z, routeMode);
        }

        function onTravelExecuteRequested(riskAcknowledged) {
            if (window.backend)
                window.backend.executeTravel(riskAcknowledged);
        }

        function onSectorScanRequested(x, y, z) {
            if (window.backend)
                window.backend.scanSector(x, y, z);
        }

        function onNeighboringSectorsScanRequested() {
            if (window.backend)
                window.backend.scanNeighboringSectors();
        }

        function onAutonomousTravelTargetRequested(x, y, z) {
            if (window.backend)
                window.backend.setAutonomousTravelTarget(x, y, z);
        }

        function onApiKeySaveRequested(apiKey) {
            if (window.backend) window.backend.saveApiKey(apiKey);
        }

        function onApiKeyTestRequested() {
            if (window.backend) window.backend.testApiKey();
        }

        function onApiKeyRemoveRequested() {
            if (window.backend) window.backend.removeApiKey();
        }

        function onOnboardingResetRequested() {
            if (window.backend) window.backend.resetOnboarding();
        }

        function onExecutionPolicySaveRequested(policy) {
            if (window.backend) window.backend.saveExecutionPolicy(policy);
        }

        function onAutomationCycleRequested() {
            if (window.backend) window.backend.runAutomationCycle();
        }

        function onAutomationApprovalRequested(fingerprint, riskAcknowledged) {
            if (window.backend) window.backend.approveAutomationCommand(fingerprint, riskAcknowledged);
        }

        function onTransportCycleSaveRequested(plan) {
            if (window.backend) window.backend.saveTransportCycle(plan);
        }

        function onProbeRenameRequested(name) {
            if (window.backend) window.backend.renameFocusedProbe(name);
        }

        function onContainerRenameRequested(containerId, label) {
            if (window.backend) window.backend.renameStorageContainer(containerId, label);
        }

        function onStorageRulesSaveRequested(containerId, rules) {
            if (window.backend) window.backend.saveStorageRules(containerId, rules);
        }

        function onStorageMoveRequested(payload) {
            if (window.backend) window.backend.moveStorage(payload);
        }

        function onLogbookCreateRequested(title, content) {
            if (window.backend) window.backend.createLogbookPage(title, content);
        }

        function onLogbookUpdateRequested(pageId, title, content) {
            if (window.backend) window.backend.updateLogbookPage(pageId, title, content);
        }

        function onLogbookDeleteRequested(pageId) {
            if (window.backend) window.backend.deleteLogbookPage(pageId);
        }

        function onAutoLogbookChanged(enabled) {
            if (window.backend) window.backend.setAutoLogbookEnabled(enabled);
        }

        function onLogbookPageOpenRequested(pageId) {
            if (window.backend) window.backend.loadLogbookPage(pageId);
        }
    }
}
