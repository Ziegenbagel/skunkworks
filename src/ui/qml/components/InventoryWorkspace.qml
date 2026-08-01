pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var inventoryData: ({})
    property var pendingMove: ({})
    signal probeRenameRequested(string name)
    signal containerRenameRequested(string containerId, string label)
    signal storageRulesSaveRequested(string containerId, var rules)
    signal storageMoveRequested(var payload)

    function splitRules(value) {
        return String(value || "").split(",").map(item => item.trim()).filter(item => item.length > 0);
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
                title: "PROBE IDENTITY"; Layout.fillWidth: true
                RowLayout {
                    anchors.fill: parent
                    Label { text: "CURRENT NAME · " + (root.inventoryData.probeName || "Probe"); color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
                    TextField { id: probeName; Layout.fillWidth: true; placeholderText: "New probe name" }
                    Button { text: "RENAME PROBE"; enabled: probeName.text.trim().length > 0; onClicked: root.probeRenameRequested(probeName.text) }
                }
            }

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

            Label { text: "CONTAINERS & ROUTING RULES"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true }
            GridLayout {
                id: containerGrid; Layout.fillWidth: true; columns: root.width >= 1200 ? 2 : 1; columnSpacing: 18; rowSpacing: 18
                Repeater {
                    model: root.inventoryData.containers || []
                    delegate: Rectangle {
                        id: containerCard; required property var modelData
                        Layout.preferredWidth: (root.width - (containerGrid.columns - 1) * containerGrid.columnSpacing) / containerGrid.columns
                        implicitHeight: containerControls.implicitHeight + 36; color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4
                        ColumnLayout {
                            id: containerControls; anchors.fill: parent; anchors.margins: 18; spacing: 10
                            Label { Layout.fillWidth: true; text: String(containerCard.modelData.label || containerCard.modelData.id).toUpperCase() + " · " + Number(containerCard.modelData.usedCapacity || 0).toFixed(2) + " / " + Number(containerCard.modelData.capacity || 0).toFixed(2) + " ECE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true; wrapMode: Text.Wrap }
                            RowLayout { Layout.fillWidth: true; TextField { id: containerLabel; Layout.fillWidth: true; placeholderText: "New container label" } Button { text: "RENAME"; enabled: containerLabel.text.trim().length > 0; onClicked: root.containerRenameRequested(String(containerCard.modelData.id), containerLabel.text) } }
                            Label { text: "Comma-separated inventory types, such as metals, ice, manny, scut_relay"; color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
                            TextField { id: priorityRules; Layout.fillWidth: true; placeholderText: "Priority routing"; text: (containerCard.modelData.rules && containerCard.modelData.rules.priority || []).join(", ") }
                            TextField { id: exclusionRules; Layout.fillWidth: true; placeholderText: "Exclusion routing"; text: (containerCard.modelData.rules && containerCard.modelData.rules.exclusion || []).join(", ") }
                            TextField { id: strictRules; Layout.fillWidth: true; placeholderText: "Strict exclusion"; text: (containerCard.modelData.rules && containerCard.modelData.rules.strictExclusion || []).join(", ") }
                            Button { text: "SAVE ROUTING RULES"; Layout.alignment: Qt.AlignRight; onClicked: root.storageRulesSaveRequested(String(containerCard.modelData.id), {"priority": root.splitRules(priorityRules.text), "exclusion": root.splitRules(exclusionRules.text), "strictExclusion": root.splitRules(strictRules.text)}) }
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
                        implicitHeight: itemDetails.implicitHeight + 28; color: Constants.panelColor; border.color: Constants.lineColor; radius: 3
                        ColumnLayout { id: itemDetails; anchors.fill: parent; anchors.margins: 14
                            Label { Layout.fillWidth: true; text: itemCard.modelData.name; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true; wrapMode: Text.Wrap }
                            Label { Layout.fillWidth: true; text: String(itemCard.modelData.type).replaceAll("_", " ").toUpperCase() + " · " + itemCard.modelData.containerLabel + " · " + Number(itemCard.modelData.containerSpace).toFixed(2) + " ECE"; color: Constants.mutedTextColor; font.pixelSize: 13; wrapMode: Text.Wrap }
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
}
