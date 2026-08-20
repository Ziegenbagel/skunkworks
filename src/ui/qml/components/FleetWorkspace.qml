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
    property var sameSectorProbes: []
    property var allMannies: []
    property real deuterium: 0
    property real maximumMiningOrderAmount: 0.55
    property bool manualOnly: false
    property var mannies: []
    property var namingPolicy: ({})
    property var pendingMiningOrder: ({})
    property var pendingTransferOrder: ({})
    property double currentEpochMs: Date.now()
    signal probeSelected(int probeId)
    signal probeRenameRequested(string name)
    signal mannyRenameRequested(string mannyId, string name)
    signal fleetNamingRequested(var policy, bool applyExisting)
    signal makeDefaultRequested()
    signal repairRequested(string mannyId, real integrityPercent)
    signal upgradeRequested(string mannyId, string improvementId)
    signal miningRequested(string mannyId, var payload)
    signal inventoryMannyActionRequested(string action, string mannyId, var payload)

    function selectedIntegerId(combo) {
        if (!combo || combo.currentIndex < 0)
            return -1;
        const value = Number(combo.currentValue);
        return Number.isInteger(value) && value > 0 ? value : -1;
    }

    function movementSummary(probe) {
        const movement = probe.movement || {};
        const status = String(probe.status || "unknown").toUpperCase();
        if (["PREPARING", "ACCELERATING", "CRUISING", "DECELERATING", "TRAVELING"].indexOf(status) < 0)
            return "";
        const journey = probe.transportJourney || {};
        const itinerary = journey.active
            ? "\n" + String(journey.journeyLabel || "AUTO-TRAVEL") + " · HOP " + Number(journey.hopNumber || 1)
              + " OF " + Number(journey.totalHops || 1)
              + " · FINAL " + String(journey.finalDestinationLabel || "UNKNOWN")
              + (journey.showFinalArrivalEstimate
                    ? " · TRIP ETA " + journeyRemainingLabel(journey.estimatedFinalArrivalEpochMs)
                    : "")
              + "\nITINERARY · " + (journey.itinerary || []).map(function(hop) {
                    return (Number(hop.number) === Number(journey.hopNumber) ? "▶ " : "")
                           + Number(hop.number) + ". " + String(hop.label);
                }).join("  →  ")
            : "";
        return "TRANSIT · " + status
            + "\nORIGIN " + String(movement.originLabel || "UNKNOWN")
            + "  ·  ARRIVAL SECTOR " + String(movement.destinationLabel || "UNKNOWN")
            + "\nREMAINING " + remainingLabel(movement)
            + "  ·  VELOCITY C " + String(movement.velocity || probe.velocity || "—")
            + "  ·  HEADING " + headingLabel(movement.heading) + itinerary;
    }

    function journeyRemainingLabel(epochMs) {
        if (Number(epochMs || 0) <= 0) return "RECALCULATING";
        const seconds = Math.max(0, Math.floor((Number(epochMs) - root.currentEpochMs) / 1000));
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainder = seconds % 60;
        return (hours ? hours + " HR " : "") + minutes + " MIN " + remainder + " S";
    }

    function remainingLabel(movement) {
        if (Number(movement.arrivalEpochMs || 0) > 0) {
            const seconds = Math.max(0, Math.floor((Number(movement.arrivalEpochMs) - root.currentEpochMs) / 1000));
            return readableDuration(seconds);
        }
        const raw = movement.remainingTime;
        if (raw !== undefined && raw !== null) {
            if (typeof raw === "number") {
                const seconds = Math.max(0, Math.floor(raw));
                return readableDuration(seconds);
            }
            return String(raw);
        }
        if (movement.estimatedArrival) {
            const seconds = Math.max(0, Math.floor((Date.parse(movement.estimatedArrival) - Date.now()) / 1000));
            if (!isNaN(seconds)) return readableDuration(seconds);
        }
        return "AWAITING TELEMETRY";
    }
    function readableDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainder = seconds % 60;
        return (hours > 0 ? hours + " HR " : "") + minutes + " MIN " + remainder + " S";
    }
    function headingLabel(heading) {
        if (!heading) return "—";
        if (typeof heading === "object") return [heading.x || 0, heading.y || 0, heading.z || 0].join(":");
        return String(heading);
    }

    function namingExample(template) {
        const probe = String(root.probeData.name || "Focused Probe");
        const number = sequenceStyle.currentValue === "letters"
            ? "A" : String(1).padStart(numberDigits.value, "0");
        let output = String(template || "");
        return output.replace(/\{probe\}/g, probe)
                     .replace(/\{number(?::0*\d+d)?\}/g, number);
    }

    function simpleMannyTemplate() {
        return String(root.namingPolicy.mannyTemplate || "{probe}-M{number}")
            .replace(/\{number(?::0*\d+d)?\}/g, "{number}");
    }

    function namingDigits() {
        if (root.namingPolicy.numberDigits !== undefined)
            return Math.max(1, Math.min(6, Number(root.namingPolicy.numberDigits)));
        const legacy = String(root.namingPolicy.mannyTemplate || "").match(/\{number:([0-9]+)d\}/);
        return legacy ? Math.max(1, Math.min(6, legacy[1].length)) : 2;
    }

    function syncNamingControls() {
        namingEnabled.checked = Boolean(root.namingPolicy.enabled);
        mannyNamingTemplate.text = root.simpleMannyTemplate();
        sequenceStyle.currentIndex = String(root.namingPolicy.sequenceStyle || "numeric") === "letters" ? 1 : 0;
        numberDigits.value = root.namingDigits();
    }

    onNamingPolicyChanged: Qt.callLater(root.syncNamingControls)
    onFocusedProbeIdChanged: Qt.callLater(root.syncNamingControls)
    Component.onCompleted: root.syncNamingControls()

    Timer {
        interval: 1000
        running: root.visible
        repeat: true
        triggeredOnStart: true
        onTriggered: root.currentEpochMs = Date.now()
    }

    ScrollView {
        id: fleetPageScroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
        width: Math.max(1, fleetPageScroll.availableWidth)
        spacing: 14
        Label { visible: !root.manualOnly; text: "FLEET & PROBE IDENTITY"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
        RowLayout {
            visible: !root.manualOnly
            Layout.fillWidth: true
            Label { text: "RENAME FOCUSED PROBE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
            TextField { id: probeName; Layout.fillWidth: true; placeholderText: "New probe name" }
            Button { text: "RENAME"; enabled: probeName.text.trim().length > 0; onClicked: root.probeRenameRequested(probeName.text) }
            Button {
                text: "MAKE DEFAULT"
                enabled: root.focusedProbeId >= 0 && root.probes.some(function(item) { return Number(item.id) === root.focusedProbeId && !item.isDefault && item.isReachable; })
                onClicked: makeDefaultConfirmation.open()
            }
        }
        Label {
            visible: !root.manualOnly
            Layout.fillWidth: true
            text: "Default-probe reassignment requires the current default and focused probe to share a sector or active SCUT network. Unreachable probes cannot be selected."
            color: Constants.mutedTextColor; font.pixelSize: 13; wrapMode: Text.Wrap
        }
        GroupBox {
            visible: !root.manualOnly
            title: "MANNY AUTO-NAMING · FOCUSED PROBE"; Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent
                spacing: 9

                Label {
                    Layout.fillWidth: true
                    text: "These settings belong only to the focused probe. Auto-name New applies the saved pattern to Mannys first discovered after you save it; Apply to Existing renames this probe's current Mannys. Probe names are never changed automatically."
                    color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 13; wrapMode: Text.Wrap
                }
                RowLayout {
                    Layout.fillWidth: true; spacing: 16
                    CheckBox { id: namingEnabled; text: "AUTO-NAME NEW MANNYS" }
                    Label {
                        Layout.fillWidth: true
                        text: "The focused probe's current name is substituted wherever {probe} appears."
                        color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 12; wrapMode: Text.Wrap
                    }
                }
                GridLayout {
                    Layout.fillWidth: true; columns: 3; columnSpacing: 12; rowSpacing: 7
                    Label { text: "NAME FORMAT"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    TextField { id: mannyNamingTemplate; placeholderText: "{probe}-M{number}"; Layout.fillWidth: true }
                    Label { text: "EXAMPLE MANNY · " + root.namingExample(mannyNamingTemplate.text); color: Constants.textColor; font.family: Constants.technicalFont }

                    Label { text: "SEQUENCE STYLE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    ComboBox {
                        id: sequenceStyle; textRole: "text"; valueRole: "value"
                        model: [{"text":"NUMERIC", "value":"numeric"}, {"text":"LETTERS", "value":"letters"}]
                    }
                    Label { text: sequenceStyle.currentValue === "letters" ? "A … Z, Aa, Ab … Az, Ba …" : "1, 2, 3 … with optional leading zeroes"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }

                    Label { visible: sequenceStyle.currentValue === "numeric"; text: "TOTAL NUMBER DIGITS"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    SpinBox { visible: sequenceStyle.currentValue === "numeric"; id: numberDigits; from: 1; to: 6; editable: true }
                    Label { visible: sequenceStyle.currentValue === "numeric"; text: "1 → 1   ·   2 → 01   ·   3 → 001"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                }
                Label {
                    Layout.fillWidth: true
                    text: "FORMAT FIELDS · {probe} inserts the focused probe name · {number} inserts the numeric or letter sequence selected above."
                    color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 12; wrapMode: Text.Wrap
                }
                RowLayout {
                    Layout.fillWidth: true
                    Button { text: "SAVE NAMING SETTINGS"; onClicked: root.fleetNamingRequested({"enabled":namingEnabled.checked,"mannyTemplate":mannyNamingTemplate.text,"numberDigits":numberDigits.value,"sequenceStyle":sequenceStyle.currentValue}, false) }
                    Button { text: "APPLY TO EXISTING MANNYS"; onClicked: root.fleetNamingRequested({"enabled":namingEnabled.checked,"mannyTemplate":mannyNamingTemplate.text,"numberDigits":numberDigits.value,"sequenceStyle":sequenceStyle.currentValue}, true) }
                    Label { Layout.fillWidth: true; text: "Apply Existing renames this focused probe's Mannys immediately."; color: Constants.warningColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                }
            }
        }
        RowLayout {
            visible: !root.manualOnly
            Layout.fillWidth: true
            Label { text: "RENAME MANNY"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
            ComboBox { id: renameMannyChoice; Layout.preferredWidth: 280; model: root.mannies; textRole: "name"; valueRole: "id" }
            TextField { id: mannyName; Layout.fillWidth: true; placeholderText: "New Manny name" }
            Button { text: "RENAME"; enabled: renameMannyChoice.currentIndex >= 0 && mannyName.text.trim().length > 0; onClicked: root.mannyRenameRequested(String(renameMannyChoice.currentValue), mannyName.text) }
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
                        textFromValue: function(value, locale) {
                            return String(miningResource.currentText) === "deuterium"
                                ? (value * 5).toFixed(0) + " ECE"
                                : (value * 0.05).toFixed(2) + " ECE"
                        }
                        valueFromText: function(text, locale) {
                            const amount = Number(String(text).replace(/[^0-9.]/g, ""));
                            const step = String(miningResource.currentText) === "deuterium" ? 5 : 0.05;
                            return Math.max(from, Math.min(to, Math.round(amount / step)));
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
        GroupBox {
            visible: root.manualOnly
            title: "SAME-SECTOR PROBE TRANSFERS"; Layout.fillWidth: true
            GridLayout {
                anchors.fill: parent; columns: 4; columnSpacing: 14; rowSpacing: 10
                Label { text: "TARGET PROBE"; color: Constants.cyanColor; font.bold: true }
                ComboBox { id: targetProbe; textRole: "name"; valueRole: "id"; model: root.sameSectorProbes; Layout.fillWidth: true }
                Label { text: "ACTION MANNY"; color: Constants.cyanColor; font.bold: true }
                ComboBox { id: transferManny; textRole: "name"; valueRole: "id"; model: root.idleMannies; Layout.fillWidth: true }
                Label { text: "DEUTERIUM AMOUNT"; color: Constants.textColor }
                RowLayout {
                    SpinBox { id: deuteriumAmount; from: 1; to: Math.max(1, Math.floor(root.deuterium * 100) - 1); value: 1; editable: true }
                    Label { text: "× 0.01 ECE"; color: Constants.mutedTextColor }
                }
                Label { Layout.fillWidth: true; text: "SOURCE RESERVE · " + root.deuterium.toFixed(2) + " ECE"; color: Constants.warningColor; wrapMode: Text.Wrap }
                Button {
                    text: "REVIEW FUEL TRANSFER"
                    enabled: root.selectedIntegerId(targetProbe) > 0 && transferManny.count > 0 && root.deuterium > 0.01
                    onClicked: {
                        root.pendingTransferOrder = {"action":"transfer-deuterium-to-probe", "mannyId":String(transferManny.currentValue), "payload":{"targetProbeId":root.selectedIntegerId(targetProbe), "amount":Number(deuteriumAmount.value) / 100}};
                        transferConfirmation.open();
                    }
                }
                Label { text: "TRANSFER MANNY"; color: Constants.textColor }
                ComboBox { id: reassignManny; textRole: "name"; valueRole: "id"; model: root.allMannies; Layout.fillWidth: true }
                Label { Layout.fillWidth: true; text: "Transferring a busy Manny cancels its current task."; color: Constants.warningColor; wrapMode: Text.Wrap }
                Button {
                    text: "REVIEW MANNY TRANSFER"
                    enabled: root.selectedIntegerId(targetProbe) > 0 && reassignManny.count > 0
                    onClicked: {
                        root.pendingTransferOrder = {"action":"transfer-to-probe", "mannyId":String(reassignManny.currentValue), "payload":{"targetProbeId":root.selectedIntegerId(targetProbe)}};
                        transferConfirmation.open();
                    }
                }
                Label { Layout.columnSpan: 4; Layout.fillWidth: true; text: targetProbe.count ? "Only probes in the focused probe's current sector are listed. Probe movement blocks transfers until both probes have arrived." : "No other owned probe is currently observed in this sector."; color: Constants.mutedTextColor; font.pixelSize: 14; wrapMode: Text.Wrap }
            }
        }
        GridLayout {
            id: fleetGrid
            visible: !root.manualOnly
            Layout.fillWidth: true
            columns: fleetPageScroll.availableWidth >= 1050 ? 2 : 1
            columnSpacing: 18; rowSpacing: 18
            Repeater {
                model: root.probes
                delegate: Rectangle {
                    id: probeCard; required property var modelData
                    Layout.fillWidth: true
                    Layout.minimumWidth: 300
                    Layout.preferredWidth: Math.max(300, (fleetGrid.width - (fleetGrid.columns - 1) * fleetGrid.columnSpacing) / fleetGrid.columns)
                    // Keep the grid stable as probes enter and leave transit.
                    // This is the traveling-card height plus buffer for wrapped
                    // telemetry on narrower windows.
                    Layout.minimumHeight: 210
                    Layout.preferredHeight: 210
                    Layout.maximumHeight: 210
                    color: probeCard.modelData.id === root.focusedProbeId ? Constants.selectedColor : Constants.raisedColor; border.color: probeCard.modelData.id === root.focusedProbeId ? Constants.cyanColor : Constants.lineColor; radius: 4
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

    Dialog {
        id: transferConfirmation; anchors.centerIn: parent; modal: true
        title: "CONFIRM SAME-SECTOR TRANSFER"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.inventoryMannyActionRequested(String(root.pendingTransferOrder.action), String(root.pendingTransferOrder.mannyId), root.pendingTransferOrder.payload || ({}))
        Label {
            width: 560
            text: "This sends a live same-sector transfer order. Verify the focused probe, target probe, Manny, and fuel amount before continuing. Transferring a busy Manny cancels its current task."
            color: Constants.textColor; font.pixelSize: 15; wrapMode: Text.Wrap
        }
    }

    Dialog {
        id: makeDefaultConfirmation; anchors.centerIn: parent; modal: true
        title: "CONFIRM DEFAULT PROBE CHANGE"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.makeDefaultRequested()
        Label { width: 560; text: "The focused probe becomes the account's default probe and primary reference for reachable telemetry and default-only controls. Confirm both probes are in the same sector or connected through the same active SCUT network."; color: Constants.textColor; wrapMode: Text.Wrap }
    }
}
