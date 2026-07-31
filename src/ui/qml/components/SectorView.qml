pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property string sectorLabel: "FCC 0 / 0 / 0"
    color: "#09141c"
    border.color: Constants.lineColor
    clip: true

    Repeater {
        model: [0.28, 0.52, 0.76]
        delegate: Rectangle {
            required property real modelData
            width: Math.min(root.width, root.height) * modelData
            height: width
            anchors.centerIn: parent
            radius: width / 2
            color: "transparent"
            border.color: Qt.rgba(Constants.cyanColor.r, Constants.cyanColor.g, Constants.cyanColor.b, 0.22)
            border.width: 1
        }
    }

    Rectangle { anchors.horizontalCenter: parent.horizontalCenter; width: 1; height: parent.height; color: Qt.rgba(0.33, 0.78, 0.85, 0.18) }
    Rectangle { anchors.verticalCenter: parent.verticalCenter; height: 1; width: parent.width; color: Qt.rgba(0.33, 0.78, 0.85, 0.18) }

    Rectangle {
        anchors.centerIn: parent
        width: 16
        height: 16
        radius: 8
        color: Constants.cyanColor
        border.color: Constants.textColor
        Label {
            anchors.left: parent.right
            anchors.leftMargin: 7
            anchors.verticalCenter: parent.verticalCenter
            text: "MANNY ONE"
            color: Constants.textColor
            font.family: Constants.technicalFont
            font.pixelSize: 8
        }
    }

    Rectangle {
        x: root.width * 0.68
        y: root.height * 0.30
        width: 21
        height: 21
        radius: 11
        color: Constants.warningColor
        Label {
            anchors.left: parent.right
            anchors.leftMargin: 7
            text: "D-42 · DEUTERIUM"
            color: Constants.warningColor
            font.family: Constants.technicalFont
            font.pixelSize: 8
        }
    }

    Rectangle {
        x: root.width * 0.24
        y: root.height * 0.64
        width: 13
        height: 13
        rotation: 45
        color: Constants.noticeColor
        Label {
            anchors.left: parent.right
            anchors.leftMargin: 8
            text: "DEPOT MN-184"
            color: Constants.noticeColor
            font.family: Constants.technicalFont
            font.pixelSize: 8
            rotation: -45
        }
    }

    Row {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 10
        spacing: 14
        Label { text: root.sectorLabel; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
        Label { text: "LIVE · DETAILED"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
    }
}
