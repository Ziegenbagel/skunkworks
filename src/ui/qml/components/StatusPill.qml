import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property string label: "NOMINAL"
    property color statusColor: Constants.nominalColor
    implicitWidth: statusLabel.implicitWidth + 28
    implicitHeight: 26
    radius: 13
    color: Qt.rgba(statusColor.r, statusColor.g, statusColor.b, 0.12)
    border.color: statusColor

    Label {
        id: statusLabel
        anchors.centerIn: parent
        text: root.label
        color: root.statusColor
        font.family: Constants.technicalFont
        font.pixelSize: 10
        font.bold: true
    }
}
