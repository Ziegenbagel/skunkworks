import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root
    property string label: "SYSTEM"
    property real value: 0.5
    property string reading: "50%"
    property color accentColor: Constants.cyanColor
    implicitHeight: 54
    height: implicitHeight

    Label {
        id: metricLabel
        anchors.left: parent.left
        anchors.top: parent.top
        text: root.label
        color: Constants.mutedTextColor
        font.family: Constants.technicalFont
        font.pixelSize: 11
    }

    Label {
        anchors.right: parent.right
        anchors.top: parent.top
        text: root.reading
        color: root.accentColor
        font.family: Constants.technicalFont
        font.pixelSize: 12
        font.bold: true
    }

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: metricLabel.bottom
        anchors.topMargin: 8
        height: 14
        color: Constants.voidColor
        border.color: Constants.lineColor

        Rectangle {
            width: parent.width * Math.max(0, Math.min(1, root.value))
            height: parent.height
            color: root.accentColor
        }
    }
}
