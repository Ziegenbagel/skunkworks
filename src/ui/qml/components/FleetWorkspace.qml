pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var probes: []
    property int focusedProbeId: -1
    signal probeSelected(int probeId)
    signal probeRenameRequested(string name)

    ColumnLayout {
        anchors.fill: parent; spacing: 14
        Label { text: "FLEET & PROBE IDENTITY"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
        RowLayout {
            Layout.fillWidth: true
            Label { text: "RENAME FOCUSED PROBE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
            TextField { id: probeName; Layout.fillWidth: true; placeholderText: "New probe name" }
            Button { text: "RENAME"; enabled: probeName.text.trim().length > 0; onClicked: root.probeRenameRequested(probeName.text) }
        }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            GridLayout {
                id: fleetGrid; width: root.width; columns: root.width >= 1050 ? 2 : 1; columnSpacing: 18; rowSpacing: 18
                Repeater {
                    model: root.probes
                    delegate: Rectangle {
                        id: probeCard; required property var modelData
                        Layout.preferredWidth: (root.width - (fleetGrid.columns - 1) * fleetGrid.columnSpacing) / fleetGrid.columns
                        implicitHeight: 120; color: probeCard.modelData.id === root.focusedProbeId ? Constants.selectedColor : Constants.raisedColor; border.color: probeCard.modelData.id === root.focusedProbeId ? Constants.cyanColor : Constants.lineColor; radius: 4
                        ColumnLayout { anchors.fill: parent; anchors.margins: 18
                            Label { Layout.fillWidth: true; text: probeCard.modelData.name + (probeCard.modelData.id === root.focusedProbeId ? " · FOCUSED" : ""); color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 17; font.bold: true }
                            Label { Layout.fillWidth: true; text: String(probeCard.modelData.model || "generic").split("_").join(" ").toUpperCase() + " · " + String(probeCard.modelData.status || "unknown").toUpperCase(); color: Constants.mutedTextColor; font.pixelSize: 15 }
                            Label { Layout.fillWidth: true; text: probeCard.modelData.sectorLabel || "SECTOR UNKNOWN"; color: Constants.cyanColor; font.pixelSize: 14 }
                        }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.probeSelected(Number(probeCard.modelData.id)) }
                    }
                }
            }
        }
    }
}
