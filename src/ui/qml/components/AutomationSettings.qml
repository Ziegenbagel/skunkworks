pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var settingsData: ({})
    property var availableProbes: []
    property var credentialData: ({})
    signal saveRequested(var settings)
    signal roleAssignmentRequested(int probeId, string role)
    signal apiKeySaveRequested(string apiKey)
    signal apiKeyTestRequested()
    signal apiKeyRemoveRequested()
    signal onboardingResetRequested()
    readonly property var roleOptions: ["unassigned", "hub", "miner", "transport", "deuterium_tanker", "deuterium_reserve", "explorer", "builder_support"]

    function productionQuantity(recipeId) {
        const rows = settingsData.production || [];
        for (let i = 0; i < rows.length; ++i)
            if (rows[i].recipeId === recipeId) return Number(rows[i].quantity || 0);
        return 0;
    }
    function productionPriority(recipeId) {
        const rows = settingsData.production || [];
        for (let i = 0; i < rows.length; ++i)
            if (rows[i].recipeId === recipeId) return Number(rows[i].priority || 50);
        return 50;
    }
    function reserve(resource) { return Number((settingsData.resourceReserves || {})[resource] || 0); }
    function roleFor(probeId) { return (settingsData.probeRoles || {})[String(probeId)] || "unassigned"; }
    function payload() {
        const production = [];
        const existing = settingsData.production || [];
        for (let i = 0; i < existing.length; ++i)
            if (existing[i].recipeId !== "manny" && existing[i].recipeId !== "additional_container")
                production.push(existing[i]);
        production.push({"recipeId": "manny", "quantity": mannyTarget.value, "priority": mannyPriority.value});
        production.push({"recipeId": "additional_container", "quantity": containerTarget.value, "priority": containerPriority.value});
        return {
            "fleetTargets": {"generic": genericTarget.value, "deuterium_tanker": tankerTarget.value},
            "fleetPriorities": {"generic": genericPriority.value, "deuterium_tanker": tankerPriority.value},
            "production": production,
            "resourceReserves": {
                "deuterium": deuteriumReserve.value, "metals": metalsReserve.value,
                "ice": iceReserve.value, "carbon_compounds": carbonReserve.value
            },
            "resourcePriorities": {
                "deuterium": deuteriumPriority.value, "metals": metalsPriority.value,
                "ice": icePriority.value, "carbon_compounds": carbonPriority.value
            },
            "minimumFuelPercent": fuelFloor.value,
            "fuelPriority": fuelPriority.value,
            "minimumFreeCapacity": freeCapacity.value,
            "inventoryPriority": capacityPriority.value,
            "travelTarget": settingsData.travelTarget || null
        };
    }

    ScrollView {
        anchors.fill: parent; clip: true
        ColumnLayout {
            width: root.width - 24; spacing: 14
            Label { text: "AUTOMATION DESIRED STATE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 13; font.bold: true }
            Label { Layout.fillWidth: true; text: "Targets are persistent planner goals. Priority 1 is highest. Goals never bypass safety review or the emergency stop."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }

            GroupBox {
                title: "ACCOUNT & API CREDENTIAL"; Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent; spacing: 8
                    Label { Layout.fillWidth: true; text: "The key is stored in the operating-system credential vault and is never written into Skunkworks settings or logs."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                    RowLayout {
                        Layout.fillWidth: true
                        TextField { id: settingsApiKey; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: root.credentialData.configured ? "API key configured · enter a replacement to change it" : "Paste Von Neumann API key" }
                        Button { text: "SAVE SECURELY"; enabled: settingsApiKey.text.length > 0; onClicked: { root.apiKeySaveRequested(settingsApiKey.text); settingsApiKey.clear(); } }
                        Button { text: "TEST CONNECTION"; enabled: Boolean(root.credentialData.configured); onClicked: root.apiKeyTestRequested() }
                        Button { text: "REMOVE"; enabled: Boolean(root.credentialData.configured); onClicked: root.apiKeyRemoveRequested() }
                    }
                    Label { text: root.credentialData.configured ? "CONFIGURED · " + String(root.credentialData.source || "vault").split("_").join(" ").toUpperCase() : "NOT CONFIGURED"; color: root.credentialData.configured ? Constants.nominalColor : Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                    Label { visible: Boolean(root.credentialData.message); Layout.fillWidth: true; text: root.credentialData.message || ""; color: Constants.cyanColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                    Button { text: "RUN FIRST-LAUNCH WALKTHROUGH AGAIN"; onClicked: root.onboardingResetRequested() }
                }
            }

            GroupBox {
                title: "FLEET ASSEMBLY TARGETS"; Layout.fillWidth: true
                GridLayout {
                    anchors.fill: parent; columns: 3; columnSpacing: 18; rowSpacing: 10
                    Label { text: "AUTOMATION TARGET"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.bold: true }
                    Label { text: "DESIRED QUANTITY"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    Label { text: "PRIORITY · 1 IS HIGHEST"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                    Label { text: "GENERIC PROBES"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: genericTarget; from: 0; to: 99; value: Number((root.settingsData.fleetTargets || {}).generic || 0) }
                    SpinBox { id: genericPriority; from: 1; to: 999; value: Number((root.settingsData.fleetPriorities || {}).generic || 50) }
                    Label { text: "DEUTERIUM TANKERS"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                    SpinBox { id: tankerTarget; from: 0; to: 99; value: Number((root.settingsData.fleetTargets || {}).deuterium_tanker || 0) }
                    SpinBox { id: tankerPriority; from: 1; to: 999; value: Number((root.settingsData.fleetPriorities || {}).deuterium_tanker || 10) }
                    Label { text: "MANNYS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: mannyTarget; from: 0; to: 999; value: root.productionQuantity("manny") }
                    SpinBox { id: mannyPriority; from: 1; to: 999; value: root.productionPriority("manny") }
                    Label { text: "ADDITIONAL CONTAINERS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: containerTarget; from: 0; to: 999; value: root.productionQuantity("additional_container") }
                    SpinBox { id: containerPriority; from: 1; to: 999; value: root.productionPriority("additional_container") }
                }
            }

            GroupBox {
                title: "OWNED PROBE ROLES"; Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent; spacing: 8
                    Label { Layout.fillWidth: true; text: "Roles guide mining, transport, hub, tanker, reserve, exploration, and construction planning."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                    Repeater {
                        model: root.availableProbes
                        delegate: RowLayout {
                            id: probeRoleRow
                            required property var modelData
                            Layout.fillWidth: true
                            Label { Layout.preferredWidth: 250; text: probeRoleRow.modelData.name; color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true }
                            Label { Layout.preferredWidth: 180; text: String(probeRoleRow.modelData.model || "generic").split("_").join(" ").toUpperCase(); color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                            ComboBox {
                                id: roleSelector
                                Layout.preferredWidth: 230
                                model: root.roleOptions
                                currentIndex: Math.max(0, root.roleOptions.indexOf(root.roleFor(probeRoleRow.modelData.id)))
                                onActivated: root.roleAssignmentRequested(Number(probeRoleRow.modelData.id), String(currentText))
                            }
                            Label { Layout.fillWidth: true; text: probeRoleRow.modelData.sectorLabel || "SECTOR UNKNOWN"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                        }
                    }
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
                            text: "P" + modelData.priority + "  ·  " + String(modelData.model).split("_").join(" ").toUpperCase() + "  ·  " + modelData.current + " CURRENT / " + modelData.target + " TARGET  ·  " + modelData.shortage + " TO ASSEMBLE"
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
                    anchors.fill: parent; columns: 3; columnSpacing: 18; rowSpacing: 10
                    Label { text: "AUTOMATION FLOOR"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.bold: true }
                    Label { text: "MINIMUM QUANTITY"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    Label { text: "PRIORITY · 1 IS HIGHEST"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                    Label { text: "DEUTERIUM"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: deuteriumReserve; from: 0; to: 100000; value: root.reserve("deuterium") }
                    SpinBox { id: deuteriumPriority; from: 1; to: 999; value: Number((root.settingsData.resourcePriorities || {}).deuterium || 50) }
                    Label { text: "METALS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: metalsReserve; from: 0; to: 100000; value: root.reserve("metals") }
                    SpinBox { id: metalsPriority; from: 1; to: 999; value: Number((root.settingsData.resourcePriorities || {}).metals || 50) }
                    Label { text: "ICE"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: iceReserve; from: 0; to: 100000; value: root.reserve("ice") }
                    SpinBox { id: icePriority; from: 1; to: 999; value: Number((root.settingsData.resourcePriorities || {}).ice || 50) }
                    Label { text: "CARBON COMPOUNDS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: carbonReserve; from: 0; to: 100000; value: root.reserve("carbon_compounds") }
                    SpinBox { id: carbonPriority; from: 1; to: 999; value: Number((root.settingsData.resourcePriorities || {}).carbon_compounds || 50) }
                    Label { text: "FUEL FLOOR %"; color: Constants.warningColor; font.family: Constants.technicalFont }
                    SpinBox { id: fuelFloor; from: 0; to: 100; value: Number(root.settingsData.minimumFuelPercent || 20) }
                    SpinBox { id: fuelPriority; from: 1; to: 999; value: Number(root.settingsData.fuelPriority || 30) }
                    Label { text: "MIN FREE CAPACITY"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: freeCapacity; from: 0; to: 1000; value: Number(root.settingsData.minimumFreeCapacity || 1) }
                    SpinBox { id: capacityPriority; from: 1; to: 999; value: Number(root.settingsData.inventoryPriority || 30) }
                }
            }

            Button { text: "SAVE AUTOMATION TARGETS"; Layout.alignment: Qt.AlignRight; onClicked: root.saveRequested(root.payload()) }
        }
    }
}
