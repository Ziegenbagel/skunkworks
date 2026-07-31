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
}
