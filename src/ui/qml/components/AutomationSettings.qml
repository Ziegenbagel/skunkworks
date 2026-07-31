pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var settingsData: ({})
    signal saveRequested(var settings)

    function productionQuantity(recipeId) {
        const rows = settingsData.production || [];
        for (let i = 0; i < rows.length; ++i)
            if (rows[i].recipeId === recipeId) return Number(rows[i].quantity || 0);
        return 0;
    }
    function reserve(resource) { return Number((settingsData.resourceReserves || {})[resource] || 0); }
    function payload() {
        const production = [];
        const existing = settingsData.production || [];
        for (let i = 0; i < existing.length; ++i)
            if (existing[i].recipeId !== "manny" && existing[i].recipeId !== "additional_container")
                production.push(existing[i]);
        production.push({"recipeId": "manny", "quantity": mannyTarget.value});
        production.push({"recipeId": "additional_container", "quantity": containerTarget.value});
        return {
            "fleetTargets": {"generic": genericTarget.value, "deuterium_tanker": tankerTarget.value},
            "production": production,
            "resourceReserves": {
                "deuterium": deuteriumReserve.value, "metals": metalsReserve.value,
                "ice": iceReserve.value, "carbon_compounds": carbonReserve.value
            },
            "minimumFuelPercent": fuelFloor.value,
            "minimumFreeCapacity": freeCapacity.value,
            "travelTarget": settingsData.travelTarget || null
        };
    }

    ScrollView {
        anchors.fill: parent; clip: true
        ColumnLayout {
            width: root.width - 24; spacing: 14
            Label { text: "AUTOMATION DESIRED STATE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 13; font.bold: true }
            Label { Layout.fillWidth: true; text: "Targets are persistent planner goals. They do not bypass safety review or the emergency stop."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }

            GroupBox {
                title: "FLEET ASSEMBLY TARGETS"; Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent; columns: 3; columnSpacing: 18; rowSpacing: 10
                    Label { text: "GENERIC PROBES"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: genericTarget; from: 0; to: 99; value: Number((root.settingsData.fleetTargets || {}).generic || 0) }
                    Label { text: "Manny assemble-probe workflow"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                    Label { text: "DEUTERIUM TANKERS"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                    SpinBox { id: tankerTarget; from: 0; to: 99; value: Number((root.settingsData.fleetTargets || {}).deuterium_tanker || 0) }
                    Label { text: "Requires two empty containers per tanker"; color: Constants.warningColor; font.family: Constants.technicalFont }
                    Label { text: "MANNYS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: mannyTarget; from: 0; to: 999; value: root.productionQuantity("manny") }
                    Label { text: "Crafted inventory target"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                    Label { text: "ADDITIONAL CONTAINERS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: containerTarget; from: 0; to: 999; value: root.productionQuantity("additional_container") }
                    Label { text: "Crafted inventory target"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                }
            }

            GroupBox {
                title: "LIVE TARGET STATUS"; Layout.fillWidth: true
                Column {
                    width: parent.width; spacing: 6
                    Repeater {
                        model: root.settingsData.fleetStatus || []
                        delegate: Label {
                            required property var modelData
                            text: String(modelData.model).split("_").join(" ").toUpperCase() + "  ·  " + modelData.current + " CURRENT / " + modelData.target + " TARGET  ·  " + modelData.shortage + " TO ASSEMBLE"
                            color: modelData.shortage > 0 ? Constants.warningColor : Constants.nominalColor
                            font.family: Constants.technicalFont
                        }
                    }
                    Label {
                        visible: !(root.settingsData.fleetStatus || []).length
                        text: "SAVE FLEET TARGETS, THEN REFRESH TO CALCULATE LIVE SHORTAGES"
                        color: Constants.mutedTextColor; font.family: Constants.technicalFont
                    }
                }
            }

            GroupBox {
                title: "RESOURCE & SAFETY FLOORS"; Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent; columns: 4; columnSpacing: 18; rowSpacing: 10
                    Label { text: "DEUTERIUM"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: deuteriumReserve; from: 0; to: 100000; value: root.reserve("deuterium") }
                    Label { text: "METALS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: metalsReserve; from: 0; to: 100000; value: root.reserve("metals") }
                    Label { text: "ICE"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: iceReserve; from: 0; to: 100000; value: root.reserve("ice") }
                    Label { text: "CARBON COMPOUNDS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: carbonReserve; from: 0; to: 100000; value: root.reserve("carbon_compounds") }
                    Label { text: "FUEL FLOOR %"; color: Constants.warningColor; font.family: Constants.technicalFont }
                    SpinBox { id: fuelFloor; from: 0; to: 100; value: Number(root.settingsData.minimumFuelPercent || 20) }
                    Label { text: "MIN FREE CAPACITY"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: freeCapacity; from: 0; to: 1000; value: Number(root.settingsData.minimumFreeCapacity || 1) }
                }
            }

            Button { text: "SAVE AUTOMATION TARGETS"; Layout.alignment: Qt.AlignRight; onClicked: root.saveRequested(root.payload()) }
        }
    }
}
