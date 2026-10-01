pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ColumnLayout {
    id: root
    property string role: ""
    property var settings: ({})
    property var runtime: ({})
    property var receivers: []
    property var components: root.runtime.componentOptions || []
    ListModel { id: packageRows }
    signal saveRequested(var settings)
    spacing: 12
    function relaySettings() {
        return {infrastructureEnabled: enabledRole.checked,
            expansionMode: autoMode.checked ? "auto" : signalMode.checked ? "signal" : "direction",
            beaconMode: ["final", "every", "none"][beaconMode.currentIndex],
            home: {x: homeX.value, y: homeY.value, z: homeZ.value},
            direction: {x: directionX.value, y: directionY.value, z: directionZ.value},
            relayStock: restockCount.value,
            refillBeacons: refillBeacons.checked,
            beaconStock: beaconStock.value};
    }
    function hubSettings(request) {
        const result = {infrastructureEnabled: enabledRole.checked, receiveContainers: receiveContainers.checked};
        if (request) result.enqueuePackage = request;
        return result;
    }
    function packageItems() {
        let items = {};
        for (let i = 0; i < packageRows.count; ++i) {
            const row = packageRows.get(i);
            items[row.componentId] = (items[row.componentId] || 0) + row.quantity;
        }
        return items;
    }
    function addComponent() {
        if (root.components.length)
            packageRows.append({componentId: String(root.components[0].id), quantity: 1});
    }
    function itemSummary(items) {
        return Object.keys(items || {}).filter(function(key) { return items[key] > 0; }).map(function(key) {
            const option = root.components.find(function(c) { return c.id === key; });
            return items[key] + " × " + (option ? option.name : key.replace(/_/g, " "));
        }).join(", ");
    }
    Label {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: String(root.runtime.phase || "NOT EVALUATED").replace(/_/g, " ").toUpperCase()
              + "\n" + String(root.runtime.summary || "Save settings and evaluate an automation cycle to see the next action.")
        color: Constants.cyanColor; font.family: Constants.technicalFont
    }
    CheckBox { id: enabledRole; palette.windowText: Constants.textColor; text: root.role === "hub" ? "ENABLE HUB SUPPLY" : "ENABLE SCUT NETWORK EXPANSION"; checked: Boolean(root.settings.infrastructureEnabled) }
    ButtonGroup { id: expansionModes }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "relay_placement"; title: "1 · AUTOMATIC COVERAGE EXPANSION"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent
            RadioButton { id: autoMode; ButtonGroup.group: expansionModes; text: "PICK SITES FOR NEW COVERAGE"; checked: String(root.settings.expansionMode || "auto") === "auto" }
            Label { Layout.fillWidth: true; text: "Ranks mapped stars inside current SCUT range by the new sectors their relay would cover. Scan additional sectors when no suitable site is known."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
        }
    }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "relay_placement"; title: "2 · EXPAND TOWARD THE SIGNAL"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent
            RadioButton { id: signalMode; ButtonGroup.group: expansionModes; text: "FOLLOW THE SIGNAL DIRECTION"; checked: root.settings.expansionMode === "signal" }
            Label { Layout.fillWidth: true; text: "Uses the direction and original location recorded in your anomaly alert. The source distance is unknown; each new site advances along that direction."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
        }
    }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "relay_placement"; title: "3 · EXPAND IN A CHOSEN DIRECTION"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent
            RadioButton { id: directionMode; ButtonGroup.group: expansionModes; text: "FOLLOW THESE COORDINATES FROM HOME"; checked: root.settings.expansionMode === "direction" }
            RowLayout {
                Label { text: "X / Y / Z"; color: Constants.warningColor }
                SpinBox { id: directionX; from: -100000; to: 100000; editable: true; value: Number((root.settings.direction || {}).x || 0) }
                SpinBox { id: directionY; from: -100000; to: 100000; editable: true; value: Number((root.settings.direction || {}).y || 0) }
                SpinBox { id: directionZ; from: -100000; to: 100000; editable: true; value: Number((root.settings.direction || {}).z || 0) }
            }
            Label { Layout.fillWidth: true; text: "Defines a direction from home through this sector; expansion can continue beyond it. X + Y + Z must be even."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
        }
    }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "relay_placement"; title: "BEACONS AND HOME RESTOCKING"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent; spacing: 10
            ComboBox { id: beaconMode; Layout.fillWidth: true; model: ["BEACON ON FINAL RELAY IN STOCK", "BEACON ON EVERY RELAY", "NO BEACONS"]; currentIndex: root.settings.beaconMode === "every" ? 1 : root.settings.beaconMode === "none" ? 2 : 0 }
            RowLayout {
                Label { text: "HOME X / Y / Z"; color: Constants.warningColor }
                SpinBox { id: homeX; from: -100000; to: 100000; editable: true; value: Number((root.settings.home || {}).x || 0) }
                SpinBox { id: homeY; from: -100000; to: 100000; editable: true; value: Number((root.settings.home || {}).y || 0) }
                SpinBox { id: homeZ; from: -100000; to: 100000; editable: true; value: Number((root.settings.home || {}).z || 0) }
            }
            RowLayout {
                Label { text: "RELAYS PER REFILL KIT"; color: Constants.warningColor }
                SpinBox { id: restockCount; from: 1; to: 20; value: Number(root.settings.relayStock || 4) }
            }
            Label { Layout.fillWidth: true; text: "INTEGRATED CIRCUITS · " + restockCount.value + " (ONE PER RELAY FOR ACTIVATION)"; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            CheckBox {
                id: refillBeacons
                text: "REFILL TRANSIT BEACONS AT HOME"
                checked: root.settings.refillBeacons === undefined ? beaconMode.currentIndex !== 2 : Boolean(root.settings.refillBeacons)
            }
            RowLayout {
                enabled: refillBeacons.checked
                Label { text: "BEACONS PER REFILL KIT"; color: Constants.warningColor }
                SpinBox { id: beaconStock; from: 1; to: 20; value: Number(root.settings.beaconStock || (beaconMode.currentIndex === 1 ? restockCount.value : 1)) }
            }
            Label { Layout.fillWidth: true; text: "Refill quantities are stock targets: the Hub supplies only what is missing. Beacon quantity is independent of relay quantity and beacon placement frequency. Changes apply to the next refill request."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            Label { Layout.fillWidth: true; text: "Returns home when relays, activation circuits, or required beacons run out. An enabled Hub at home builds and hands over the kit. Normal fuel, repair, Manny-return, and travel checks remain active."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            Button { text: "SAVE SCUT NETWORK EXPANSION SETTINGS"; onClicked: root.saveRequested(root.relaySettings()) }
        }
    }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "hub"; title: "PRODUCTION AND INCOMING SUPPLIES"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent
            Label { Layout.fillWidth: true; text: "Maintains the reserve and production targets configured in Automation and builds requested refill kits. Mines local resource shortages and accepts Miner and Transport deliveries."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            CheckBox { id: receiveContainers; text: "RECOVER DRIFTING SUPPLY CONTAINERS"; checked: root.settings.receiveContainers !== false }
            Button { text: "SAVE HUB ROLE SETTINGS"; onClicked: root.saveRequested(root.hubSettings(null)) }
        }
    }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "hub"; title: "CREATE A SUPPLY PACKAGE"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent; spacing: 10
            ComboBox { id: receiver; Layout.fillWidth: true; model: root.receivers; textRole: "name"; valueRole: "id" }
            Repeater {
                model: packageRows
                delegate: RowLayout {
                    id: componentRow
                    required property int index
                    required property string componentId
                    required property int quantity
                    ComboBox {
                        Layout.fillWidth: true; model: root.components; textRole: "name"; valueRole: "id"
                        currentIndex: root.components.findIndex(function(c) { return c.id === componentRow.componentId; })
                        onActivated: packageRows.setProperty(componentRow.index, "componentId", String(currentValue))
                    }
                    SpinBox { from: 1; to: 1000; editable: true; value: componentRow.quantity
                        onValueModified: packageRows.setProperty(componentRow.index, "quantity", value) }
                    Button { text: "REMOVE"; onClicked: packageRows.remove(componentRow.index) }
                }
            }
            Button { text: "ADD COMPONENT"; enabled: root.components.length > 0
                onClicked: root.addComponent() }
            Label { Layout.fillWidth: true; text: "Packages split into as many containers as needed. Each receiver unloads and returns its temporary container before receiving the next shipment. Other probes' packages can progress while a receiver is waiting."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            Button { text: "QUEUE PACKAGE"; enabled: receiver.currentIndex >= 0 && packageRows.count > 0 && enabledRole.checked
                onClicked: root.saveRequested(root.hubSettings({id: "manual-" + Date.now() + "-" + Math.random().toString(36).slice(2), targetProbeId: Number(receiver.currentValue), items: root.packageItems()}))
            }
        }
    }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "hub"; title: "SUPPLY QUEUE · PLANNED PACKAGES"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent
            Label { visible: !(root.runtime.packages || []).length; text: "No packages evaluated yet. Saved requests appear after the next automation cycle."; Layout.fillWidth: true; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            Repeater { model: root.runtime.packages || []
                delegate: Frame {
                    id: packageCard
                    required property var modelData
                    property int countWidth: width < 650 ? 58 : 82
                    Layout.fillWidth: true
                    Layout.topMargin: 8
                    padding: 16
                    background: Rectangle { color: Constants.panelColor; border.color: Constants.lineColor; radius: 4 }
                    ColumnLayout {
                        anchors.fill: parent; spacing: 12
                        Label {
                            text: packageCard.modelData.targetName
                            Layout.fillWidth: true; wrapMode: Text.Wrap
                            color: Constants.cyanColor; font.pixelSize: 18; font.bold: true
                        }
                        Label {
                            text: (packageCard.modelData.source === "automatic" ? "Automatic refill" : "Manual package")
                                + "   ·   Shipment " + (Number(packageCard.modelData.shipment || 0) + 1)
                            color: Constants.textColor; font.pixelSize: 14
                            Layout.fillWidth: true; wrapMode: Text.Wrap
                        }
                        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Constants.lineColor }
                        RowLayout {
                            Layout.fillWidth: true; spacing: 8
                            Label { text: "COMPONENT"; Layout.fillWidth: true; color: Constants.mutedTextColor; font.pixelSize: 12 }
                            Repeater { model: ["TO SEND", "TO CRAFT", "CRAFTING", "TO LOAD", "LOADED"]
                                delegate: Label {
                                    required property string modelData
                                    text: modelData; Layout.preferredWidth: packageCard.countWidth
                                    horizontalAlignment: Text.AlignRight; wrapMode: Text.Wrap
                                    color: Constants.mutedTextColor; font.pixelSize: 12
                                }
                            }
                        }
                        Repeater {
                            model: Object.keys(Object.assign({}, packageCard.modelData.items || {}, packageCard.modelData.loadedItems || {}))
                            delegate: RowLayout {
                                id: componentProgress
                                required property string modelData
                                Layout.fillWidth: true; spacing: 8
                                Label {
                                    Layout.fillWidth: true; Layout.minimumWidth: 100; wrapMode: Text.Wrap
                                    text: { const option = root.components.find(function(c) { return c.id === componentProgress.modelData; });
                                        return option ? option.name : componentProgress.modelData.replace(/_/g, " "); }
                                    color: Constants.textColor; font.pixelSize: 15
                                }
                                Repeater { model: ["items", "missingItems", "craftingItems", "availableItems", "loadedItems"]
                                    delegate: Label {
                                        required property string modelData
                                        property int count: Number((packageCard.modelData[modelData] || {})[componentProgress.modelData] || 0)
                                        text: count > 0 ? String(count) : "—"
                                        Layout.preferredWidth: packageCard.countWidth
                                        horizontalAlignment: Text.AlignRight
                                        color: count > 0 ? (modelData === "loadedItems" ? Constants.nominalColor : Constants.textColor) : Constants.mutedTextColor
                                        font.pixelSize: 15; font.family: Constants.technicalFont
                                    }
                                }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Constants.lineColor }
                        Label {
                            text: "NEXT STEP  ·  " + (packageCard.modelData.summary || "Queued for preparation.")
                            Layout.fillWidth: true; wrapMode: Text.Wrap
                            color: Constants.textColor; font.pixelSize: 14
                        }
                        Label {
                            text: "HANDOFF  ·  " + (packageCard.modelData.receiverSummary || "Waiting for receiver check")
                            Layout.fillWidth: true; wrapMode: Text.Wrap
                            color: packageCard.modelData.receiverBlocker ? Constants.warningColor : Constants.cyanColor
                            font.pixelSize: 14
                        }
                        ToolButton {
                            id: packageDetails
                            text: checked ? "Hide container details ▴" : "Container details ▾"
                            checkable: true
                        }
                        Label {
                            visible: packageDetails.checked
                            text: "Container: " + (packageCard.modelData.containerId || "Not assigned")
                            Layout.fillWidth: true; wrapMode: Text.WrapAnywhere
                            color: Constants.mutedTextColor; font.pixelSize: 13; font.family: Constants.technicalFont
                        }
                    }
                }
            }
        }
    }
}
