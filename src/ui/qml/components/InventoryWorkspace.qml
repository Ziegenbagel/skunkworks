pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var inventoryData: ({})
    property var pendingMove: ({})
    property var pendingOperation: ({})
    signal probeRenameRequested(string name)
    signal containerRenameRequested(string containerId, string label)
    signal storageRulesSaveRequested(string containerId, var rules)
    signal craftingReservationsReassignRequested(string containerId)
    signal storageMoveRequested(var payload)
    signal jettisonRequested(string itemId, real amount, string containerId)
    signal inventoryMannyActionRequested(string action, string mannyId, var payload)

    function selectedIntegerId(combo) {
        if (!combo || combo.currentIndex < 0 || !combo.model || !combo.model[combo.currentIndex])
            return -1;
        const value = Number(combo.model[combo.currentIndex].id);
        return Number.isInteger(value) && value > 0 ? value : -1;
    }

    readonly property var preferredContentOptions: [
        {"text": "ANY CONTENTS", "value": "any"},
        {"text": "METALS", "value": "metals"},
        {"text": "ICE", "value": "ice"},
        {"text": "CARBON COMPOUNDS", "value": "carbon_compounds"}
    ]
    function preferredContent(container) {
        const priority = container.rules && container.rules.priority || [];
        for (let i = 0; i < priority.length; ++i)
            if (["metals", "ice", "carbon_compounds"].indexOf(String(priority[i])) >= 0) return String(priority[i]);
        return "any";
    }
    function simpleRules(value) {
        if (value === "any") return {"priority": [], "exclusion": [], "strictExclusion": []};
        const resources = ["metals", "ice", "carbon_compounds"];
        return {"priority": [value], "exclusion": [], "strictExclusion": resources.filter(item => item !== value)};
    }
    function movePayload() {
        const payload = {
            "actorMannyId": String(actorManny.currentValue),
            "kind": moveKind.currentValue,
            "toContainerId": String(destinationContainer.currentValue)
        };
        if (moveKind.currentValue === "resource") {
            payload.fromContainerId = String(sourceContainer.currentValue);
            payload.resourceType = String(resourceType.currentValue);
            payload.amount = Number(moveAmount.value) / 100;
        } else {
            payload.itemId = String(inventoryItem.currentValue);
        }
        return payload;
    }

    ScrollView {
        anchors.fill: parent; clip: true
        ColumnLayout {
            width: root.width - 20; spacing: 18
            Label { text: "INVENTORY & CONTAINER CONTROL"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
            Label { Layout.fillWidth: true; text: "Manage the focused probe and its attached storage. Every transfer is performed by an available onboard Manny and requires confirmation."; color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 14; wrapMode: Text.Wrap }

            GroupBox {
                title: "MOVE STOCK BETWEEN CONTAINERS"; Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent; columns: 4; columnSpacing: 14; rowSpacing: 10
                    Label { text: "AVAILABLE MANNY"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    ComboBox { id: actorManny; textRole: "name"; valueRole: "id"; model: root.inventoryData.idleMannies || []; Layout.fillWidth: true }
                    Label { text: "MOVE TYPE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    ComboBox { id: moveKind; textRole: "text"; valueRole: "value"; model: [{"text":"RESOURCE", "value":"resource"}, {"text":"ITEM / EQUIPMENT", "value":"item"}]; Layout.fillWidth: true }
                    Label { text: moveKind.currentValue === "resource" ? "RESOURCE" : "ITEM"; color: Constants.textColor; font.family: Constants.technicalFont }
                    ComboBox { id: resourceType; visible: moveKind.currentValue === "resource"; model: ["metals", "ice", "carbon_compounds"]; Layout.fillWidth: true }
                    ComboBox { id: inventoryItem; visible: moveKind.currentValue === "item"; textRole: "name"; valueRole: "id"; model: root.inventoryData.items || []; Layout.fillWidth: true }
                    Label { visible: moveKind.currentValue === "resource"; text: "AMOUNT"; color: Constants.textColor }
                    RowLayout { visible: moveKind.currentValue === "resource"; SpinBox { id: moveAmount; from: 1; to: 100000; value: 5 } Label { text: "× 0.01 ECE"; color: Constants.mutedTextColor } }
                    Item { visible: moveKind.currentValue === "item" }
                    Item { visible: moveKind.currentValue === "item" }
                    Label { visible: moveKind.currentValue === "resource"; text: "FROM"; color: Constants.textColor }
                    ComboBox { id: sourceContainer; visible: moveKind.currentValue === "resource"; textRole: "label"; valueRole: "id"; model: root.inventoryData.containers || []; Layout.fillWidth: true }
                    Label { text: "DESTINATION"; color: Constants.textColor }
                    ComboBox { id: destinationContainer; textRole: "label"; valueRole: "id"; model: root.inventoryData.containers || []; Layout.fillWidth: true }
                    Label { Layout.columnSpan: 3; Layout.fillWidth: true; text: actorManny.count ? "The selected Manny becomes busy for the duration of this storage move." : "No idle onboard Manny is currently available to perform a transfer."; color: actorManny.count ? Constants.mutedTextColor : Constants.warningColor; font.pixelSize: 14; wrapMode: Text.Wrap }
                    Button { text: "REVIEW TRANSFER"; enabled: actorManny.count > 0 && destinationContainer.count > 0 && (moveKind.currentValue === "item" ? inventoryItem.count > 0 : sourceContainer.currentValue !== destinationContainer.currentValue); onClicked: { root.pendingMove = root.movePayload(); transferConfirmation.open(); } }
                }
            }

            GroupBox {
                title: "MANUAL JETTISON & ITEM HANDOFF"; Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent; columns: 4; columnSpacing: 14; rowSpacing: 10
                    Label { text: "CONTENT TYPE"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: jettisonKind; model: ["RESOURCE STOCK", "ITEM / EQUIPMENT"]; Layout.fillWidth: true }
                    Label { text: jettisonKind.currentIndex === 0 ? "RESOURCE LOCATION" : "STORED ITEM"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: jettisonResource; visible: jettisonKind.currentIndex === 0; textRole: "displayText"; valueRole: "id"; model: root.inventoryData.resourcePlacements || []; Layout.fillWidth: true }
                    ComboBox { id: jettisonItem; visible: jettisonKind.currentIndex === 1; textRole: "name"; valueRole: "id"; model: (root.inventoryData.items || []).filter(item => item.canJettison); Layout.fillWidth: true }
                    Label { visible: jettisonKind.currentIndex === 0; text: "AMOUNT"; color: Constants.textColor }
                    RowLayout { visible: jettisonKind.currentIndex === 0; SpinBox { id: jettisonAmount; from: 1; to: Math.max(1, Math.floor(Number(jettisonResource.currentIndex >= 0 ? jettisonResource.model[jettisonResource.currentIndex].amount : 0) * 100)); value: Math.min(5, to) } Label { text: "× 0.01 ECE"; color: Constants.mutedTextColor } }
                    Label { Layout.columnSpan: 3; Layout.fillWidth: true; text: "Jettisoned contents become recoverable sector objects. For an item handoff, jettison here, switch to the receiving probe in the same sector, then use Recover drifting object below."; color: Constants.warningColor; font.pixelSize: 14; wrapMode: Text.Wrap }
                    Button {
                        text: "REVIEW JETTISON"; enabled: jettisonKind.currentIndex === 0 ? jettisonResource.count > 0 : jettisonItem.count > 0
                        onClicked: {
                            const placement = jettisonResource.currentIndex >= 0 ? jettisonResource.model[jettisonResource.currentIndex] : {};
                            root.pendingOperation = {"kind":"jettison", "itemId": jettisonKind.currentIndex === 0 ? String(jettisonResource.currentValue) : String(jettisonItem.currentValue), "amount": jettisonKind.currentIndex === 0 ? Number(jettisonAmount.value) / 100 : 0, "containerId": jettisonKind.currentIndex === 0 ? String(placement.containerId || "") : ""};
                            operationConfirmation.open();
                        }
                    }
                }
            }

            GroupBox {
                title: "CONTAINER DEPLOYMENT, RECOVERY & PROBE HANDOFF"; Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent; columns: 4; columnSpacing: 14; rowSpacing: 10
                    Label { text: "AVAILABLE MANNY"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: containerManny; textRole: "name"; valueRole: "id"; model: root.inventoryData.idleMannies || []; Layout.fillWidth: true }
                    Label { text: "ATTACHED CONTAINER"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: deployContainer; textRole: "label"; valueRole: "id"; model: (root.inventoryData.containers || []).filter(item => item.kind === "container" || item.type === "additional_container"); Layout.fillWidth: true }
                    Label { text: "DESTINATION"; color: Constants.textColor }
                    ComboBox { id: deployMode; textRole: "text"; valueRole: "value"; model: [{"text":"DRIFTING IN SPACE", "value":"drifting"}, {"text":"HIDDEN ON ASTEROID", "value":"asteroid"}, {"text":"PLACED ON PLANET", "value":"planet"}, {"text":"TRANSFER TO PROBE", "value":"probe"}]; Layout.fillWidth: true }
                    Label { visible: deployMode.currentValue !== "drifting"; text: "SECTOR OBJECT"; color: Constants.textColor }
                    ComboBox { id: deployTarget; visible: deployMode.currentValue !== "drifting"; textRole: "name"; valueRole: "id"; model: deployMode.currentValue === "probe" ? (root.inventoryData.sameSectorProbes || []) : (root.inventoryData.sectorTargets || []).filter(item => item.type === deployMode.currentValue); Layout.fillWidth: true }
                    Label { Layout.columnSpan: 3; Layout.fillWidth: true; text: deployMode.currentValue === "planet" ? "Planet placement consumes an Atmospheric Drop Kit." : deployMode.currentValue === "probe" ? "The game transfers this whole attached container directly to the selected same-sector probe." : deployMode.currentValue === "drifting" ? "The container becomes a visible drifting object that can later be recovered by a Manny." : "The container will be concealed on the selected asteroid and remains recoverable after detection."; color: Constants.warningColor; font.pixelSize: 14; wrapMode: Text.Wrap }
                    Button { text: "REVIEW DEPLOYMENT"; enabled: containerManny.count > 0 && deployContainer.count > 0 && (deployMode.currentValue === "drifting" || deployTarget.count > 0); onClicked: { const action = deployMode.currentValue === "planet" ? "drop-storage-container" : "detach-storage-container"; const mode = deployMode.currentValue === "asteroid" ? "hidden_on_asteroid" : deployMode.currentValue === "probe" ? "attach_to_probe" : "drifting"; const payload = deployMode.currentValue === "planet" ? {"containerId":String(deployContainer.currentValue), "planetId":String(deployTarget.currentValue)} : {"containerId":String(deployContainer.currentValue), "mode":mode, "objectId":deployMode.currentValue === "drifting" ? "" : String(deployTarget.currentValue)}; root.pendingOperation = {"kind":"manny", "action":action, "mannyId":String(containerManny.currentValue), "payload":payload}; operationConfirmation.open(); } }

                    Label { text: "RECOVERY MANNY"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: recoveryManny; textRole: "name"; valueRole: "id"; model: root.inventoryData.idleMannies || []; Layout.fillWidth: true }
                    Label { text: "DRIFTING OBJECT"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: recoveryObject; textRole: "name"; valueRole: "id"; model: root.inventoryData.recoverableObjects || []; Layout.fillWidth: true }
                    Item { Layout.columnSpan: 3; Layout.fillWidth: true }
                    Button { text: "REVIEW RECOVERY"; enabled: recoveryManny.count > 0 && recoveryObject.count > 0; onClicked: { const object = recoveryObject.model[recoveryObject.currentIndex]; const isContainer = String(object.type).indexOf("container") >= 0; root.pendingOperation = {"kind":"manny", "action":isContainer ? "recover-storage-container" : "salvage", "mannyId":String(recoveryManny.currentValue), "payload":isContainer ? {"objectId":String(recoveryObject.currentValue), "source":object.mode === "hidden_on_asteroid" ? "asteroid" : "drifting"} : {"objectId":String(recoveryObject.currentValue)}}; operationConfirmation.open(); } }
                }
            }

            GroupBox {
                title: "MANUAL MINING DESTINATION"; Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent; columns: 4; columnSpacing: 14; rowSpacing: 10
                    Label { text: "AVAILABLE MANNY"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: miningManny; textRole: "name"; valueRole: "id"; model: root.inventoryData.idleMannies || []; Layout.fillWidth: true }
                    Label { text: "MINING TARGET"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: miningTarget; textRole: "name"; valueRole: "id"; model: root.inventoryData.miningTargets || []; Layout.fillWidth: true }
                    Label { text: "RESOURCE"; color: Constants.textColor }
                    ComboBox { id: miningResource; model: miningTarget.currentIndex >= 0 ? miningTarget.model[miningTarget.currentIndex].resourceTypes : []; Layout.fillWidth: true }
                    Label { text: "TOTAL ORDER"; color: Constants.textColor }
                    RowLayout { SpinBox { id: miningAmount; from: 1; to: 55; value: 5; editable: true } Label { text: String(miningResource.currentText) === "deuterium" ? "ECE DEUTERIUM" : "× 0.01 ECE"; color: Constants.mutedTextColor } }
                    Label { text: "DELIVER TO"; color: Constants.textColor }
                    ComboBox { id: miningDestination; textRole: "name"; valueRole: "id"; model: [{"id":"", "name":"PROBE · USE CONTAINER ROUTING RULES"}].concat(root.inventoryData.detachedContainers || []); Layout.fillWidth: true }
                    Label { Layout.columnSpan: 1; Layout.fillWidth: true; text: miningDestination.currentValue ? "Detached containers cannot accept deuterium." : "Resource-specific attached containers are preferred by their saved routing rules; otherwise an unassigned container is used."; color: Constants.mutedTextColor; wrapMode: Text.Wrap }
                    Button { text: "REVIEW MINING ORDER"; enabled: miningManny.count > 0 && miningTarget.count > 0 && miningResource.count > 0; onClicked: { const resource = String(miningResource.currentText); const payload = {"objectId":String(miningTarget.currentValue), "resources":[resource], "targetAmount":Number(miningAmount.value) / 100}; if (miningDestination.currentValue) payload.targetContainerId = String(miningDestination.currentValue); root.pendingOperation = {"kind":"manny", "action":"mine", "mannyId":String(miningManny.currentValue), "payload":payload}; operationConfirmation.open(); } }
                }
            }

            GroupBox {
                title: "SAME-SECTOR PROBE TRANSFERS"; Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent; columns: 4; columnSpacing: 14; rowSpacing: 10
                    Label { text: "TARGET PROBE"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: targetProbe; textRole: "name"; valueRole: "id"; model: root.inventoryData.sameSectorProbes || []; Layout.fillWidth: true }
                    Label { text: "ACTION MANNY"; color: Constants.cyanColor; font.bold: true }
                    ComboBox { id: transferManny; textRole: "name"; valueRole: "id"; model: root.inventoryData.idleMannies || []; Layout.fillWidth: true }
                    Label { text: "DEUTERIUM AMOUNT"; color: Constants.textColor }
                    RowLayout { SpinBox { id: deuteriumAmount; from: 1; to: Math.max(1, Math.floor(Number(root.inventoryData.deuterium || 0) * 100) - 1); value: 1; editable: true } Label { text: "× 0.01"; color: Constants.mutedTextColor } }
                    Label { Layout.columnSpan: 1; Layout.fillWidth: true; text: "SOURCE RESERVE · " + Number(root.inventoryData.deuterium || 0).toFixed(2); color: Constants.warningColor; wrapMode: Text.Wrap }
                    Button { text: "REVIEW FUEL TRANSFER"; enabled: root.selectedIntegerId(targetProbe) > 0 && transferManny.count > 0 && Number(root.inventoryData.deuterium || 0) > 0.01; onClicked: { root.pendingOperation = {"kind":"manny", "action":"transfer-deuterium-to-probe", "mannyId":String(transferManny.currentValue), "payload":{"targetProbeId":root.selectedIntegerId(targetProbe), "amount":Number(deuteriumAmount.value) / 100}}; operationConfirmation.open(); } }
                    Label { text: "TRANSFER MANNY"; color: Constants.textColor }
                    ComboBox { id: reassignManny; textRole: "name"; valueRole: "id"; model: root.inventoryData.mannies || []; Layout.fillWidth: true }
                    Label { Layout.fillWidth: true; text: "Transferring a busy Manny cancels its current task."; color: Constants.warningColor; wrapMode: Text.Wrap }
                    Button { text: "REVIEW MANNY TRANSFER"; enabled: root.selectedIntegerId(targetProbe) > 0 && reassignManny.count > 0; onClicked: { root.pendingOperation = {"kind":"manny", "action":"transfer-to-probe", "mannyId":String(reassignManny.currentValue), "payload":{"targetProbeId":root.selectedIntegerId(targetProbe)}}; operationConfirmation.open(); } }
                    Label { Layout.columnSpan: 4; Layout.fillWidth: true; text: targetProbe.count ? "Only probes in the focused probe's current sector are listed. Whole containers can be transferred directly with Container Deployment above; individual stored items use jettison and salvage." : "No other owned probe is currently observed in this sector."; color: Constants.mutedTextColor; font.pixelSize: 14; wrapMode: Text.Wrap }
                }
            }

            Label { text: "CONTAINERS & ROUTING RULES"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true }
            GridLayout {
                id: containerGrid; Layout.fillWidth: true; columns: root.width >= 1200 ? 2 : 1; columnSpacing: 18; rowSpacing: 18
                Repeater {
                    model: root.inventoryData.containers || []
                    delegate: Rectangle {
                        id: containerCard; required property var modelData
                        Layout.preferredWidth: (root.width - (containerGrid.columns - 1) * containerGrid.columnSpacing) / containerGrid.columns
                        implicitHeight: 270; color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4
                        ColumnLayout {
                            id: containerControls; anchors.fill: parent; anchors.margins: 18; spacing: 10
                            Label { Layout.fillWidth: true; text: String(containerCard.modelData.label || containerCard.modelData.id).toUpperCase() + " · " + Number(containerCard.modelData.usedCapacity || 0).toFixed(2) + " / " + Number(containerCard.modelData.capacity || 0).toFixed(2) + " ECE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true; wrapMode: Text.Wrap }
                            RowLayout { Layout.fillWidth: true; TextField { id: containerLabel; Layout.fillWidth: true; placeholderText: "New container label" } Button { text: "RENAME"; enabled: containerLabel.text.trim().length > 0; onClicked: root.containerRenameRequested(String(containerCard.modelData.id), containerLabel.text) } }
                            RowLayout {
                                Layout.fillWidth: true
                                Button { text: "REASSIGN CRAFT RESERVATIONS"; onClicked: root.craftingReservationsReassignRequested(String(containerCard.modelData.id)) }
                                Label { Layout.fillWidth: true; text: "Atomically moves active crafting-output reservations to other compatible containers. If they cannot all fit, nothing changes."; color: Constants.mutedTextColor; font.pixelSize: 12; wrapMode: Text.Wrap }
                            }
                            Label { text: "PREFERRED CONTENTS"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                            RowLayout {
                                Layout.fillWidth: true
                                ComboBox { id: preferredContents; Layout.fillWidth: true; textRole: "text"; valueRole: "value"; model: root.preferredContentOptions; Component.onCompleted: currentIndex = Math.max(0, ["any", "metals", "ice", "carbon_compounds"].indexOf(root.preferredContent(containerCard.modelData))) }
                                Button { text: "SAVE CONTENT RULE"; onClicked: root.storageRulesSaveRequested(String(containerCard.modelData.id), root.simpleRules(String(preferredContents.currentValue))) }
                            }
                            Label { Layout.fillWidth: true; text: preferredContents.currentValue === "any" ? "New resources and items may be routed here normally." : "Prioritizes " + String(preferredContents.currentText).toLowerCase() + " and prevents automatic placement of other resource categories."; color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 13; wrapMode: Text.Wrap }
                        }
                    }
                }
            }

            Label { text: "STORED ITEMS & EQUIPMENT · " + (root.inventoryData.items || []).length; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true }
            GridLayout {
                id: itemGrid; Layout.fillWidth: true; columns: root.width >= 1400 ? 3 : root.width >= 850 ? 2 : 1; columnSpacing: 12; rowSpacing: 12
                Repeater {
                    model: root.inventoryData.items || []
                    delegate: Rectangle {
                        id: itemCard; required property var modelData
                        Layout.preferredWidth: (root.width - (itemGrid.columns - 1) * itemGrid.columnSpacing) / itemGrid.columns
                        implicitHeight: 94; color: Constants.panelColor; border.color: Constants.lineColor; radius: 3
                        ColumnLayout { id: itemDetails; anchors.fill: parent; anchors.margins: 14
                            Label { Layout.fillWidth: true; text: itemCard.modelData.name; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true; wrapMode: Text.Wrap }
                            Label { Layout.fillWidth: true; text: "STORED IN · " + String(itemCard.modelData.containerLabel || itemCard.modelData.containerId).toUpperCase(); color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 13; font.bold: true; wrapMode: Text.Wrap }
                            Label { Layout.fillWidth: true; text: String(itemCard.modelData.type).split("_").join(" ").toUpperCase() + " · " + Number(itemCard.modelData.containerSpace).toFixed(2) + " ECE"; color: Constants.mutedTextColor; font.pixelSize: 12; wrapMode: Text.Wrap }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: transferConfirmation; anchors.centerIn: parent; modal: true; title: "CONFIRM STORAGE TRANSFER"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.storageMoveRequested(root.pendingMove)
        Label { width: 520; text: "This sends a live storage-move order to the game and assigns the selected Manny. Confirm the source, destination, item/resource, and amount before continuing."; color: Constants.textColor; font.pixelSize: 15; wrapMode: Text.Wrap }
    }

    Dialog {
        id: operationConfirmation; anchors.centerIn: parent; modal: true; title: "CONFIRM LIVE INVENTORY ORDER"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (root.pendingOperation.kind === "jettison") root.jettisonRequested(root.pendingOperation.itemId, root.pendingOperation.amount, root.pendingOperation.containerId);
            else root.inventoryMannyActionRequested(root.pendingOperation.action, root.pendingOperation.mannyId, root.pendingOperation.payload);
        }
        Label { width: 560; text: "This sends a live order to the game. Jettisoning and deployment remove contents or containers from the focused probe; Manny reassignment can cancel active work. Verify the selected source, target, amount, and focused probe before continuing."; color: Constants.textColor; font.pixelSize: 15; wrapMode: Text.Wrap }
    }
}
