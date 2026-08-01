pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

RowLayout {
    id: root

    property var sections: ["MISSION CONTROL", "FLEET", "GALAXY MAP", "NAVIGATION", "RESOURCES", "MISSIONS", "PRODUCTION", "RESEARCH", "SAFETY", "LOGBOOK", "SETTINGS"]
    property string currentSection: "MISSION CONTROL"
    signal sectionSelected(string section)

    spacing: 3

    Repeater {
        model: root.sections
        delegate: Rectangle {
            id: navigationItem
            required property string modelData
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: navigationItem.modelData === root.currentSection ? Constants.selectedColor : navigationMouse.containsMouse ? Constants.raisedColor : "transparent"
            border.color: navigationItem.modelData === root.currentSection ? Constants.cyanColor : "transparent"

            Label {
                anchors.centerIn: parent
                width: parent.width - 4
                text: navigationItem.modelData
                color: navigationItem.modelData === root.currentSection ? Constants.cyanColor : Constants.mutedTextColor
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                font.family: Constants.technicalFont
                font.pixelSize: 8
                font.bold: navigationItem.modelData === root.currentSection
            }

            MouseArea {
                id: navigationMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onContainsMouseChanged: if (containsMouse) AudioManager.hover()
                onClicked: root.sectionSelected(navigationItem.modelData)
            }
        }
    }
}
