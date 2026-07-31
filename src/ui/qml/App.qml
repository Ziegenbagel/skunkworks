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
        anchors.fill: parent
    }
}
