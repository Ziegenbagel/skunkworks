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
    property var miningTargets: []
    property var detachedContainers: []
    property real maximumMiningOrderAmount: 0.55
    property bool manualOnly: false
    property var pendingMiningOrder: ({})
    signal probeSelected(int probeId)
    signal probeRenameRequested(string name)
    signal repairRequested(string mannyId, real integrityPercent)
    signal upgradeRequested(string mannyId, string improvementId)
    signal miningRequested(string mannyId, var payload)

    function movementSummary(probe) {
        const movement = probe.movement || {};
        const status = String(probe.status || "unknown").toUpperCase();
        if (["PREPARING", "ACCELERATING", "CRUISING", "DECELERATING", "TRAVELING"].indexOf(status) < 0)
            return "";
        return "TRANSIT · " + status
            + " · DESTINATION " + String(movement.destinationLabel || movement.destination || "UNKNOWN")
            + " · VELOCITY " + String(movement.velocity || probe.velocity || "—")
            + " · ARRIVAL " + String(movement.estimatedArrival || movement.eta || "AWAITING TELEMETRY");
    }

    ColumnLayout {
        anchors.fill: parent; spacing: 14
        Label { visible: !root.manualOnly; text: "FLEET & PROBE IDENTITY"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
        RowLayout {
            visible: !root.manualOnly
            Layout.fillWidth: true
            Label { text: "RENAME FOCUSED PROBE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
            TextField { id: probeName; Layout.fillWidth: true; placeholderText: "New probe name" }
            Button { text: "RENAME"; enabled: probeName.text.trim().length > 0; onClicked: root.probeRenameRequested(probeName.text) }
        }
        GroupBox {
            visible: root.manualOnly
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
            visible: root.manualOnly
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
        GroupBox {
            visible: root.manualOnly
            title: "MANUAL MINING ORDER"; Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent; spacing: 8
                RowLayout {
                    Layout.fillWidth: true; spacing: 12
                    Label { text: "MANNY"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    ComboBox { id: miningManny; Layout.preferredWidth: 220; model: root.idleMannies; textRole: "name"; valueRole: "id" }
                    Label { text: "MINEABLE OBJECT"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    ComboBox { id: miningTarget; Layout.fillWidth: true; model: root.miningTargets; textRole: "name"; valueRole: "id" }
                    Label { text: "RESOURCE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    ComboBox {
                        id: miningResource; Layout.preferredWidth: 220
                        model: miningTarget.currentIndex >= 0 ? (root.miningTargets[miningTarget.currentIndex] || {}).resourceTypes || [] : []
                    }
                    Label { text: "AMOUNT"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    SpinBox {
                        id: miningAmount; editable: true; from: 1
                        to: Math.max(1, Math.min(11, Math.round(root.maximumMiningOrderAmount / 0.05)))
                        value: Math.min(5, to)
                        textFromValue: function(value, locale) { return (value * 0.05).toFixed(2) + " ECE" }
                        valueFromText: function(text, locale) {
                            const amount = Number(String(text).replace(/[^0-9.]/g, ""));
                            return Math.max(from, Math.min(to, Math.round(amount / 0.05)));
                        }
                    }
                    Label { text: "DELIVER TO"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    ComboBox {
                        id: miningDestination
                        Layout.preferredWidth: 300
                        textRole: "displayName"
                        valueRole: "id"
                        model: [{"id": "", "displayName": "ATTACHED STORAGE · USE ROUTING RULES"}].concat(
                            root.detachedContainers.map(container => ({
                                "id": String(container.id || ""),
                                "displayName": String(container.name || "Detached container")
                                    + " · " + Number(container.freeCapacity || 0).toFixed(2)
                                    + "/" + Number(container.capacity || 0).toFixed(2) + " ECE FREE"
                            })))
                    }
                    Button {
                        text: "REVIEW MINING ORDER"
                        enabled: miningManny.currentIndex >= 0 && miningTarget.currentIndex >= 0 && miningResource.currentIndex >= 0
                        onClicked: {
                            const payload = {
                                "objectId": String(miningTarget.currentValue),
                                "resources": [String(miningResource.currentText)],
                                "targetAmount": Number((miningAmount.value * 0.05).toFixed(2))
                            };
                            if (miningDestination.currentValue)
                                payload.targetContainerId = String(miningDestination.currentValue);
                            root.pendingMiningOrder = {
                                "mannyId": String(miningManny.currentValue),
                                "payload": payload
                            };
                            miningConfirmation.open();
                        }
                    }
                }
                Label {
                    Layout.fillWidth: true
                    text: "Attached storage follows the focused probe's container routing rules. A detached container may be selected explicitly when the game API reports it as a valid destination. The amount is capped by this probe's Max per Manny mining order setting."
                    color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 13; wrapMode: Text.Wrap
                }
            }
        }
        ScrollView {
            visible: !root.manualOnly
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            GridLayout {
                id: fleetGrid; width: root.width; columns: root.width >= 1050 ? 2 : 1; columnSpacing: 18; rowSpacing: 18
                Repeater {
                    model: root.probes
                    delegate: Rectangle {
                        id: probeCard; required property var modelData
                        Layout.preferredWidth: (root.width - (fleetGrid.columns - 1) * fleetGrid.columnSpacing) / fleetGrid.columns
                        implicitHeight: root.movementSummary(probeCard.modelData) ? 152 : 120; color: probeCard.modelData.id === root.focusedProbeId ? Constants.selectedColor : Constants.raisedColor; border.color: probeCard.modelData.id === root.focusedProbeId ? Constants.cyanColor : Constants.lineColor; radius: 4
                        ColumnLayout { anchors.fill: parent; anchors.margins: 18
                            Label { Layout.fillWidth: true; text: probeCard.modelData.name + (probeCard.modelData.id === root.focusedProbeId ? " · FOCUSED" : ""); color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 17; font.bold: true }
                            Label { Layout.fillWidth: true; text: String(probeCard.modelData.model || "generic").split("_").join(" ").toUpperCase() + " · " + String(probeCard.modelData.status || "unknown").toUpperCase(); color: Constants.mutedTextColor; font.pixelSize: 15 }
                            Label { Layout.fillWidth: true; text: probeCard.modelData.sectorLabel || "SECTOR UNKNOWN"; color: Constants.cyanColor; font.pixelSize: 14 }
                            Label { visible: root.movementSummary(probeCard.modelData) !== ""; Layout.fillWidth: true; text: root.movementSummary(probeCard.modelData); color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 13; wrapMode: Text.Wrap }
                        }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.probeSelected(Number(probeCard.modelData.id)) }
                    }
                }
            }
        }
    }

    Dialog {
        id: miningConfirmation; anchors.centerIn: parent; modal: true
        title: "CONFIRM MANUAL MINING ORDER"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.miningRequested(String(root.pendingMiningOrder.mannyId), root.pendingMiningOrder.payload || ({}))
        Label {
            width: 540
            text: "This sends a live mining order to the selected idle Manny. Confirm the focused probe, mineable object, resource, and amount before continuing."
            color: Constants.textColor; font.pixelSize: 15; wrapMode: Text.Wrap
        }
    }
}
