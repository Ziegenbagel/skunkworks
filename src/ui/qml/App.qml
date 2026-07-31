import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: window
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
    }

    Connections {
        target: missionControl.probeSelectorControl

        function onProbeSelected(probeId) {
            missionControl.focusedProbeId = probeId;
        }

        function onRefreshRequested() {
            // The Python controller will replace this seam with an account
            // refresh when live API testing is enabled.
            console.info("Focused probe refresh requested");
        }
    }
}
