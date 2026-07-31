import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: window
    width: Constants.width
    height: Constants.height
    minimumWidth: 1120
    minimumHeight: 700
    visible: true
    title: "Skunkworks Mission Control"
    color: Constants.voidColor

    MissionControlScreen {
        anchors.fill: parent
    }
}
