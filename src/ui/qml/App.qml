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
    }
}
