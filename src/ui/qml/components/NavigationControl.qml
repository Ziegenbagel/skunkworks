pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var navigationData: ({})
    property var travelPreview: ({})
    property var automationData: ({})
    signal previewRequested(int x, int y, int z, string routeMode)
    signal executeRequested(bool riskAcknowledged)
    signal scanRequested(int x, int y, int z)
    signal autonomousTargetRequested(int x, int y, int z)

    function chooseSector(sector) {
        targetX.value = Number(sector.x); targetY.value = Number(sector.y); targetZ.value = Number(sector.z);
    }
    readonly property bool validCoordinates: (targetX.value + targetY.value + targetZ.value) % 2 === 0

    ColumnLayout {
        anchors.fill: parent; spacing: 10
        RowLayout {
            Layout.fillWidth: true
            Label { text: "FOCUSED PROBE NAVIGATION"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true; font.pixelSize: 13 }
            Item { Layout.fillWidth: true }
            Label { text: root.navigationData.current ? root.navigationData.current.label : "SECTOR UNKNOWN"; color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true }
            Label { text: String(root.navigationData.probeStatus || "unknown").toUpperCase(); color: root.navigationData.travelReady ? Constants.nominalColor : Constants.warningColor; font.family: Constants.technicalFont }
            Label { text: Math.round(root.navigationData.fuelPercent || 0) + "% FUEL"; color: Constants.cyanColor; font.family: Constants.technicalFont }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            GroupBox {
                title: "MANUAL & AUTONOMOUS TRAVEL"; Layout.preferredWidth: 535; Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; spacing: 9
                    Label { text: "DESTINATION FCC COORDINATES"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                    RowLayout {
                        Label { text: "X"; color: Constants.textColor }
                        SpinBox { id: targetX; from: -9999; to: 9999; editable: true }
                        Label { text: "Y"; color: Constants.textColor }
                        SpinBox { id: targetY; from: -9999; to: 9999; editable: true }
                        Label { text: "Z"; color: Constants.textColor }
                        SpinBox { id: targetZ; from: -9999; to: 9999; editable: true }
                    }
                    Label { text: root.validCoordinates ? "VALID FCC COORDINATES" : "INVALID · X + Y + Z MUST BE EVEN"; color: root.validCoordinates ? Constants.nominalColor : Constants.criticalColor; font.family: Constants.technicalFont }
                    RowLayout {
                        Label { text: "ROUTE"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                        ComboBox { id: routeMode; model: ["segmented", "direct"]; Layout.preferredWidth: 170 }
                        Button { text: "PREVIEW MANUAL TRAVEL"; enabled: root.validCoordinates; onClicked: root.previewRequested(targetX.value, targetY.value, targetZ.value, String(routeMode.currentText)) }
                    }
                    Button {
                        text: "SET AS AUTONOMOUS DESTINATION"
                        enabled: root.validCoordinates
                        onClicked: root.autonomousTargetRequested(targetX.value, targetY.value, targetZ.value)
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.automationData.travelTarget ? "CURRENT AUTOMATION TARGET · FCC " + root.automationData.travelTarget.x + " / " + root.automationData.travelTarget.y + " / " + root.automationData.travelTarget.z : "NO AUTONOMOUS TRAVEL TARGET"
                        color: root.automationData.travelTarget ? Constants.cyanColor : Constants.mutedTextColor
                        font.family: Constants.technicalFont; wrapMode: Text.Wrap
                    }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Constants.lineColor }
                    Label { text: root.travelPreview.targetLabel ? "ROUTE PREVIEW · " + root.travelPreview.targetLabel : "NO ROUTE PREVIEW"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    Label {
                        Layout.fillWidth: true
                        text: root.travelPreview.targetLabel ? "SELECTED " + String(root.travelPreview.selectedRoute).toUpperCase() + " · NEXT COMMAND " + root.travelPreview.executionLabel + " · RECOMMENDED " + String(root.travelPreview.recommendedRoute).toUpperCase() : "Choose a destination or nearby sector, then preview before sending a movement command."
                        color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap
                    }
                    Repeater {
                        model: root.travelPreview.hazards || []
                        delegate: Label {
                            required property var modelData
                            Layout.fillWidth: true; text: "⚠ " + modelData.message
                            color: modelData.severity === "critical" ? Constants.criticalColor : Constants.warningColor
                            font.family: Constants.technicalFont; wrapMode: Text.Wrap
                        }
                    }
                    CheckBox { id: acknowledgeRisk; visible: Boolean(root.travelPreview.acknowledgementRequired); text: "I acknowledge the displayed travel risks" }
                    Button {
                        text: "CONFIRM NEXT TRAVEL COMMAND"
                        enabled: Boolean(root.travelPreview.canExecute) && (!root.travelPreview.acknowledgementRequired || acknowledgeRisk.checked)
                        onClicked: root.executeRequested(acknowledgeRisk.checked)
                    }
                }
            }

            GroupBox {
                title: "NEARBY SECTOR SCAN & SCUT COVERAGE"; Layout.fillWidth: true; Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent; spacing: 8
                    Label { Layout.fillWidth: true; text: "Scanning is passive API observation. SCUT coverage is calculated from live relay positions and coverage radii."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                    ListView {
                        id: neighborList
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 5
                        model: root.navigationData.neighbors || []
                        delegate: Rectangle {
                            id: neighborRow
                            required property var modelData
                            required property int index
                            width: neighborList.width; height: 48
                            color: neighborMouse.containsMouse ? Constants.selectedColor : index % 2 ? Constants.panelColor : Constants.raisedColor
                            border.color: modelData.scutCoverage && modelData.scutCoverage.covered ? Constants.nominalColor : Constants.lineColor
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 7
                                Label { Layout.preferredWidth: 150; text: neighborRow.modelData.label; color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true }
                                Label { Layout.preferredWidth: 115; text: String(neighborRow.modelData.knowledgeLevel).split("_").join(" ").toUpperCase(); color: neighborRow.modelData.visited ? Constants.cyanColor : Constants.mutedTextColor; font.family: Constants.technicalFont }
                                Label { Layout.preferredWidth: 130; text: neighborRow.modelData.scutCoverage && neighborRow.modelData.scutCoverage.covered ? "SCUT · " + neighborRow.modelData.scutCoverage.networkName : "OUTSIDE KNOWN SCUT"; color: neighborRow.modelData.scutCoverage && neighborRow.modelData.scutCoverage.covered ? Constants.nominalColor : Constants.warningColor; font.family: Constants.technicalFont }
                                Button { text: "SELECT"; onClicked: root.chooseSector(neighborRow.modelData) }
                                Button { text: "SCAN"; onClicked: root.scanRequested(neighborRow.modelData.x, neighborRow.modelData.y, neighborRow.modelData.z) }
                            }
                            MouseArea { id: neighborMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 78
                        color: Constants.panelColor; border.color: Constants.lineColor
                        Column {
                            anchors.fill: parent; anchors.margins: 9; spacing: 4
                            Label { text: root.navigationData.scanResult ? "LATEST SCAN · " + root.navigationData.scanResult.label : "NO NEARBY SCAN REQUESTED"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                            Label { width: parent.width; text: root.navigationData.scanResult ? String(root.navigationData.scanResult.knowledgeLevel).toUpperCase() + " · " + Math.round(root.navigationData.scanResult.confidence * 100) + "% CONFIDENCE · " + root.navigationData.scanResult.objectCount + " KNOWN OBJECTS · RISK " + String(root.navigationData.scanResult.dangerEstimate).toUpperCase() : "Use SCAN on any adjacent sector to request the best observation currently available."; color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                        }
                    }
                }
            }
        }
    }
}
