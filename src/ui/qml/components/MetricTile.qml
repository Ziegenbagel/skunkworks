import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property string label: "METRIC"
    property string value: "—"
    property string detail: ""
    property color accentColor: Constants.cyanColor
    implicitWidth: 150
    implicitHeight: 92
    color: Constants.raisedColor
    border.color: Constants.lineColor
    radius: 2

    Rectangle {
        width: 3
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: root.accentColor
    }

    Column {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 10
        anchors.topMargin: 12
        spacing: 3

        Label {
            text: root.label
            color: Constants.mutedTextColor
            font.family: Constants.technicalFont
            font.pixelSize: 9
            font.letterSpacing: 1
        }
        Label {
            text: root.value
            color: root.accentColor
            font.family: Constants.technicalFont
            font.pixelSize: 24
            font.bold: true
        }
        Label {
            text: root.detail
            color: Constants.mutedTextColor
            font.pixelSize: 10
        }
    }
}
