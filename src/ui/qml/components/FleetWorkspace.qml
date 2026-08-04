pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var probes: []
    property int focusedProbeId: -1
    property var probeData: ({})
    property var idleMannies: []
    property var improvements: []
    signal probeSelected(int probeId)
    signal probeRenameRequested(string name)
    signal repairRequested(string mannyId, real integrityPercent)
    signal upgradeRequested(string mannyId, string improvementId)

    ColumnLayout {
        anchors.fill: parent; spacing: 14
        Label { text: "FLEET & PROBE IDENTITY"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
        RowLayout {
            Layout.fillWidth: true
            Label { text: "RENAME FOCUSED PROBE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
            TextField { id: probeName; Layout.fillWidth: true; placeholderText: "New probe name" }
            Button { text: "RENAME"; enabled: probeName.text.trim().length > 0; onClicked: root.probeRenameRequested(probeName.text) }
        }
        GroupBox {
            title: "MANUAL PROBE REPAIR"; Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent; spacing: 12
                Label { text: "CURRENT INTEGRITY · " + Number(root.probeData.integrityPercent === undefined ? 100 : root.probeData.integrityPercent).toFixed(1) + "%"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                ComboBox { id: repairManny; Layout.preferredWidth: 240; model: root.idleMannies; textRole: "name"; valueRole: "id" }
                Label { text: "RESTORE"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                SpinBox { id: repairAmount; from: 1; to: 100; editable: true; value: Math.max(1, Math.ceil(100 - Number(root.probeData.integrityPercent === undefined ? 100 : root.probeData.integrityPercent))); textFromValue: function(value, locale) { return value + "%" }; valueFromText: function(text, locale) { return Math.max(1, Math.min(100, Number(String(text).replace(/[^0-9]/g, "")) || 1)) } }
                Button { text: "ORDER REPAIR"; enabled: repairManny.currentIndex >= 0 && root.idleMannies.length > 0 && Number(root.probeData.integrityPercent || 100) < 100; onClicked: root.repairRequested(String(repairManny.currentValue), repairAmount.value) }
                Label { Layout.fillWidth: true; text: root.idleMannies.length ? "Uses 0.01 containers of metals and 10 real minutes per restored percent." : "No idle Manny is available."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
            }
        }
        GroupBox {
            title: "MANUAL PROBE UPGRADE"; Layout.fillWidth: true
            RowLayout {
                anchors.fill: parent; spacing: 12
                ComboBox { id: upgradeChoice; Layout.fillWidth: true; model: root.improvements; textRole: "displayName"; valueRole: "id" }
                ComboBox { id: upgradeManny; Layout.preferredWidth: 240; model: root.idleMannies; textRole: "name"; valueRole: "id" }
                Button {
                    text: "INSTALL UPGRADE"
                    enabled: upgradeChoice.currentIndex >= 0 && upgradeManny.currentIndex >= 0 && root.improvements.length > 0 && root.idleMannies.length > 0
                    onClicked: root.upgradeRequested(String(upgradeManny.currentValue), String(upgradeChoice.currentValue))
                }
                Label {
                    Layout.preferredWidth: 420
                    text: root.improvements.length ? String((root.improvements[upgradeChoice.currentIndex] || {}).description || "Selected upgrade is available for this probe.") : "No unlocked, unfinished upgrade is currently available for this probe."
                    color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap
                }
            }
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
