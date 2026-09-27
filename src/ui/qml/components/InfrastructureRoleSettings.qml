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
    signal saveRequested(var settings)
    spacing: 12
    function relaySettings() {
        return {infrastructureEnabled: enabledRole.checked,
            expansionMode: autoMode.checked ? "auto" : signalMode.checked ? "signal" : "direction",
            beaconMode: ["final", "every", "none"][beaconMode.currentIndex],
            home: {x: homeX.value, y: homeY.value, z: homeZ.value},
            direction: {x: directionX.value, y: directionY.value, z: directionZ.value},
            relayStock: restockCount.value};
    }
    function hubSettings(request) {
        const result = {infrastructureEnabled: enabledRole.checked, receiveContainers: receiveContainers.checked};
        if (request) result.outputRequest = request;
        else if (settings.outputRequest) result.outputRequest = settings.outputRequest;
        return result;
    }
    Label {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: String(root.runtime.phase || "NOT EVALUATED").replace(/_/g, " ").toUpperCase()
              + "\n" + String(root.runtime.summary || "Save settings and evaluate an automation cycle to see the next action.")
        color: Constants.cyanColor; font.family: Constants.technicalFont
    }
    CheckBox { id: enabledRole; palette.windowText: Constants.textColor; text: root.role === "hub" ? "ENABLE HUB SUPPLY" : "ENABLE RELAY PLACEMENT"; checked: Boolean(root.settings.infrastructureEnabled) }
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
            Label { Layout.fillWidth: true; text: "Returns home when relays, activation circuits, or required beacons run out. An enabled Hub at home builds and hands over the kit. Normal fuel, repair, Manny-return, and travel checks remain active."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            Button { text: "SAVE RELAY ROLE SETTINGS"; onClicked: root.saveRequested(root.relaySettings()) }
        }
    }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "hub"; title: "PRODUCTION AND INCOMING SUPPLIES"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent
            Label { Layout.fillWidth: true; text: "Maintains the production targets configured in Automation and builds refill kits requested by relay probes returning here. Raw materials come from Miner and Transport deliveries."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            CheckBox { id: receiveContainers; text: "RECOVER DRIFTING SUPPLY CONTAINERS"; checked: root.settings.receiveContainers !== false }
            Button { text: "SAVE HUB ROLE SETTINGS"; onClicked: root.saveRequested(root.hubSettings(null)) }
        }
    }
    GroupBox {
        palette.windowText: Constants.textColor
        visible: root.role === "hub"; title: "SEND AN OUTPUT BATCH"; Layout.fillWidth: true
        ColumnLayout { anchors.fill: parent; spacing: 10
            ComboBox { id: receiver; Layout.fillWidth: true; model: root.receivers; textRole: "name"; valueRole: "id" }
            RowLayout {
                TextField { id: outputRecipe; Layout.fillWidth: true; placeholderText: "Recipe ID, e.g. scut_relay or steel_bar" }
                SpinBox { id: outputCount; from: 1; to: 100; value: 1 }
            }
            Label { Layout.fillWidth: true; text: "Builds and loads the selected items into a dedicated container, then hands it to the receiver when both probes are here. The receiver unloads its stock and returns the empty containers for Hub recovery before leaving. Each click requests one batch."; wrapMode: Text.Wrap; color: Constants.mutedTextColor }
            Button { text: "QUEUE OUTPUT BATCH"; enabled: receiver.currentIndex >= 0 && outputRecipe.text.trim().length > 0 && enabledRole.checked
                onClicked: { let items = {}; items[outputRecipe.text.trim()] = outputCount.value;
                    root.saveRequested(root.hubSettings({id: "manual-" + Date.now(), targetProbeId: Number(receiver.currentValue), items: items})); }
            }
        }
    }
}
