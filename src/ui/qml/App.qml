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
    }
}
