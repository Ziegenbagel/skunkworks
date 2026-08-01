pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var settingsData: ({})
    property var runtimeData: ({})
    property var availableProbes: []
    property var credentialData: ({})
    signal saveRequested(var settings)
    signal roleAssignmentRequested(int probeId, string role)
    signal apiKeySaveRequested(string apiKey)
    signal apiKeyTestRequested()
    signal apiKeyRemoveRequested()
    signal onboardingResetRequested()
    signal executionPolicySaveRequested(var policy)
    signal automationCycleRequested()
    signal automationApprovalRequested(string fingerprint, bool riskAcknowledged)
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
            if (rows[i].recipeId === recipeId) return Number(rows[i].priority || 5);
        return 5;
    }
    function reserve(resource) { return Number((settingsData.resourceReserves || {})[resource] || 0); }
    function roleFor(probeId) { return (settingsData.probeRoles || {})[String(probeId)] || "unassigned"; }
    function commandAllowed(commandType) {
        return (runtimeData.allowedCommandTypes || []).indexOf(commandType) >= 0;
    }
    function executionPolicyPayload() {
        const allowed = [];
        if (craftCommands.checked) {
            allowed.push("manny_craft");
            allowed.push("atomic_printer_craft");
            allowed.push("manny_assemble_probe");
        }
        if (miningCommands.checked) allowed.push("manny_mine");
        if (travelCommands.checked) allowed.push("move_probe");
        return {
            "mode": executionMode.currentValue,
            "liveExecutionEnabled": liveExecution.checked,
            "allowedCommandTypes": allowed,
            "maxCommandsPerCycle": commandsPerCycle.value
        };
    }
    function syncExecutionControls() {
        executionMode.currentIndex = Math.max(0, ["observe", "approve", "automatic"].indexOf(String(runtimeData.mode || "observe")));
        liveExecution.checked = Boolean(runtimeData.liveExecutionEnabled);
        commandsPerCycle.value = Number(runtimeData.maxCommandsPerCycle || 1);
        craftCommands.checked = commandAllowed("manny_craft") || commandAllowed("atomic_printer_craft") || commandAllowed("manny_assemble_probe");
        miningCommands.checked = commandAllowed("manny_mine");
        travelCommands.checked = commandAllowed("move_probe");
    }
    onRuntimeDataChanged: syncExecutionControls()
    Component.onCompleted: syncExecutionControls()
    function payload() {
        const production = [];
        const existing = settingsData.production || [];
        for (let i = 0; i < existing.length; ++i)
            if (existing[i].recipeId !== "manny" && existing[i].recipeId !== "additional_container" && existing[i].recipeId !== "scut_relay" && existing[i].recipeId !== "scut_transit_beacon")
                production.push(existing[i]);
        production.push({"recipeId": "manny", "quantity": mannyTarget.value, "priority": mannyPriority.value});
        production.push({"recipeId": "additional_container", "quantity": containerTarget.value, "priority": containerPriority.value});
        production.push({"recipeId": "scut_relay", "quantity": relayTarget.value, "priority": relayPriority.value});
        production.push({"recipeId": "scut_transit_beacon", "quantity": beaconTarget.value, "priority": beaconPriority.value});
        return {
            "priorityScaleMax": 10,
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
                title: "AUTOMATION EXECUTION"; Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent; spacing: 10
                    Label {
                        Layout.fillWidth: true
                        text: "Targets create proposed actions. Observe only previews them; Approval requires a click for each command; Automatic evaluates the queue every 60 seconds. Every command is refreshed, safety-checked, allowlisted, and stopped by the emergency stop."
                        color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap
                    }
                    GridLayout {
                        Layout.fillWidth: true; columns: 4; columnSpacing: 18; rowSpacing: 8
                        Label { text: "EXECUTION MODE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                        ComboBox {
                            id: executionMode
                            Layout.preferredWidth: 190
                            textRole: "text"; valueRole: "value"
                            model: [
                                {"text": "OBSERVE ONLY", "value": "observe"},
                                {"text": "REQUIRE APPROVAL", "value": "approve"},
                                {"text": "AUTOMATIC", "value": "automatic"}
                            ]
                        }
                        CheckBox { id: liveExecution; text: "ALLOW SKUNKWORKS TO SEND GAME ORDERS"; checked: Boolean(root.runtimeData.liveExecutionEnabled); ToolTip.visible: hovered; ToolTip.text: "Required for Approval and Automatic modes. When off, Skunkworks only plans and displays commands; it sends no POST requests to the game." }
                        RowLayout {
                            Label { text: "MAX ORDERS PER 60-SECOND CYCLE"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                            SpinBox { id: commandsPerCycle; from: 1; to: 10; value: Number(root.runtimeData.maxCommandsPerCycle || 1); ToolTip.visible: hovered; ToolTip.text: "Safety and rate limit: the most separate Manny, crafting, or travel orders Skunkworks may send in one automatic cycle." }
                        }
                        Label { text: "COMMAND ALLOWLIST"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                        CheckBox { id: craftCommands; text: "CRAFTING & PROBE ASSEMBLY"; checked: root.commandAllowed("manny_craft") || root.commandAllowed("atomic_printer_craft") || root.commandAllowed("manny_assemble_probe") }
                        CheckBox { id: miningCommands; text: "MINING"; checked: root.commandAllowed("manny_mine") }
                        CheckBox { id: travelCommands; text: "TRAVEL"; checked: root.commandAllowed("move_probe") }
                    }
                    Label {
                        visible: Boolean(root.runtimeData.emergencyStopActive)
                        text: "EMERGENCY STOP ACTIVE · NO AUTOMATION COMMANDS CAN BE SENT"
                        color: Constants.criticalColor; font.family: Constants.technicalFont; font.bold: true
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        Button { text: "SAVE EXECUTION POLICY"; onClicked: root.executionPolicySaveRequested(root.executionPolicyPayload()) }
                        Button { text: "EVALUATE / RUN ONE CYCLE"; enabled: !root.runtimeData.emergencyStopActive; onClicked: root.automationCycleRequested() }
                        Label {
                            Layout.fillWidth: true
                            text: root.runtimeData.lastResult ? String(root.runtimeData.lastResult.message || root.runtimeData.lastResult.status).toUpperCase() : "NO EXECUTION ATTEMPT THIS SESSION"
                            color: Constants.mutedTextColor; font.family: Constants.technicalFont; horizontalAlignment: Text.AlignRight
                            wrapMode: Text.Wrap
                        }
                    }
                    Label { text: "PROPOSED COMMAND QUEUE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                    Repeater {
                        model: root.runtimeData.queue || []
                        delegate: Rectangle {
                            id: commandRow
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: commandDetails.implicitHeight + 20
                            color: Constants.raisedColor; border.color: Constants.lineColor; radius: 2
                            RowLayout {
                                id: commandDetails
                                anchors.fill: parent; anchors.margins: 10; spacing: 12
                                Label { text: "P" + commandRow.modelData.priority; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 3
                                    Label { Layout.fillWidth: true; text: String(commandRow.modelData.type).split("_").join(" ").toUpperCase() + " · " + String(commandRow.modelData.disposition).split("_").join(" ").toUpperCase(); color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true }
                                    Label { Layout.fillWidth: true; text: commandRow.modelData.reason || "Proposed automation action"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                                    Label { visible: String(commandRow.modelData.type) === "manny_mine"; Layout.fillWidth: true; text: "ORDER " + Number((commandRow.modelData.metadata || {}).orderAmount || 0).toFixed(3) + " ECE · " + Number((commandRow.modelData.metadata || {}).estimatedTrips || 0) + " AUTOMATIC MANNY TRIPS · " + Number((commandRow.modelData.metadata || {}).remainingAmount || 0).toFixed(3) + " ECE STILL NEEDED"; color: Constants.cyanColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                                    Label { visible: (commandRow.modelData.blockers || []).length > 0; Layout.fillWidth: true; text: "BLOCKED · " + (commandRow.modelData.blockers || []).join(", "); color: Constants.criticalColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                                }
                                CheckBox { id: riskAcknowledgement; visible: (commandRow.modelData.warnings || []).length > 0; text: "ACKNOWLEDGE RISK" }
                                Button {
                                    text: "APPROVE"
                                    visible: String(root.runtimeData.mode) === "approve"
                                    enabled: !(commandRow.modelData.blockers || []).length && !root.runtimeData.emergencyStopActive
                                    onClicked: root.automationApprovalRequested(String(commandRow.modelData.fingerprint), riskAcknowledgement.checked)
                                }
                            }
                        }
                    }
                    Label { visible: !(root.runtimeData.queue || []).length; text: "NO ACTIONABLE COMMANDS · TARGETS MAY ALREADY BE SATISFIED OR NO READY ASSET IS AVAILABLE"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                    Label { visible: !(root.runtimeData.queue || []).length && (root.runtimeData.planning || []).length; text: "PLANNER STATUS · WHY ORDERS ARE WAITING"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                    Repeater {
                        model: !(root.runtimeData.queue || []).length ? (root.runtimeData.planning || []).slice(0, 8) : []
                        delegate: Rectangle {
                            id: waitingRow
                            required property var modelData
                            Layout.fillWidth: true; implicitHeight: waitingDetails.implicitHeight + 18
                            color: Constants.raisedColor; border.color: Constants.lineColor; radius: 2
                            ColumnLayout {
                                id: waitingDetails; anchors.fill: parent; anchors.margins: 9; spacing: 3
                                Label { Layout.fillWidth: true; text: "P" + waitingRow.modelData.priority + " · " + String(waitingRow.modelData.action).toUpperCase() + " · " + String(waitingRow.modelData.target).replace(/_/g, " ").toUpperCase(); color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true; wrapMode: Text.Wrap }
                                Label { Layout.fillWidth: true; text: waitingRow.modelData.reason; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                                Label { visible: (waitingRow.modelData.blockers || []).length > 0; Layout.fillWidth: true; text: "WAITING FOR · " + (waitingRow.modelData.blockers || []).join(", ").replace(/_/g, " ").toUpperCase(); color: Constants.warningColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                            }
                        }
                    }
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
                    SpinBox { id: genericPriority; from: 1; to: 10; value: Number((root.settingsData.fleetPriorities || {}).generic || 5) }
                    Label { text: "DEUTERIUM TANKERS"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                    SpinBox { id: tankerTarget; from: 0; to: 99; value: Number((root.settingsData.fleetTargets || {}).deuterium_tanker || 0) }
                    SpinBox { id: tankerPriority; from: 1; to: 10; value: Number((root.settingsData.fleetPriorities || {}).deuterium_tanker || 1) }
                    Label { text: "MANNYS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: mannyTarget; from: 0; to: 999; value: root.productionQuantity("manny") }
                    SpinBox { id: mannyPriority; from: 1; to: 10; value: root.productionPriority("manny") }
                    Label { text: "ADDITIONAL CONTAINERS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: containerTarget; from: 0; to: 999; value: root.productionQuantity("additional_container") }
                    SpinBox { id: containerPriority; from: 1; to: 10; value: root.productionPriority("additional_container") }
                    Label { text: "SCUT RELAYS"; color: Constants.cyanColor; font.family: Constants.technicalFont; ToolTip.visible: relayHover.hovered; ToolTip.text: "Maintain completed SCUT relays in inventory. Relay crafting can require multiple days."; HoverHandler { id: relayHover } }
                    SpinBox { id: relayTarget; from: 0; to: 99; value: root.productionQuantity("scut_relay") }
                    SpinBox { id: relayPriority; from: 1; to: 10; value: root.productionPriority("scut_relay") }
                    Label { text: "SCUT TRANSIT BEACONS"; color: Constants.cyanColor; font.family: Constants.technicalFont; ToolTip.visible: beaconHover.hovered; ToolTip.text: "Maintain transit beacons ready for installation on active SCUT relays."; HoverHandler { id: beaconHover } }
                    SpinBox { id: beaconTarget; from: 0; to: 99; value: root.productionQuantity("scut_transit_beacon") }
                    SpinBox { id: beaconPriority; from: 1; to: 10; value: root.productionPriority("scut_transit_beacon") }
                }
            }

            GroupBox {
                title: "OWNED PROBE ROLES"; Layout.fillWidth: true
                ColumnLayout {
                    anchors.fill: parent; spacing: 8
                    Label { Layout.fillWidth: true; text: "Roles guide mining, transport, hub, tanker, reserve, exploration, and construction planning. Explorer probes automatically scan all 12 neighboring FCC sectors once after arriving idle in a new sector."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
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
                    SpinBox { id: deuteriumPriority; from: 1; to: 10; value: Number((root.settingsData.resourcePriorities || {}).deuterium || 5) }
                    Label { text: "METALS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: metalsReserve; from: 0; to: 100000; value: root.reserve("metals") }
                    SpinBox { id: metalsPriority; from: 1; to: 10; value: Number((root.settingsData.resourcePriorities || {}).metals || 5) }
                    Label { text: "ICE"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: iceReserve; from: 0; to: 100000; value: root.reserve("ice") }
                    SpinBox { id: icePriority; from: 1; to: 10; value: Number((root.settingsData.resourcePriorities || {}).ice || 5) }
                    Label { text: "CARBON COMPOUNDS"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: carbonReserve; from: 0; to: 100000; value: root.reserve("carbon_compounds") }
                    SpinBox { id: carbonPriority; from: 1; to: 10; value: Number((root.settingsData.resourcePriorities || {}).carbon_compounds || 5) }
                    Label { text: "FUEL FLOOR %"; color: Constants.warningColor; font.family: Constants.technicalFont }
                    SpinBox { id: fuelFloor; from: 0; to: 100; value: Number(root.settingsData.minimumFuelPercent || 20) }
                    SpinBox { id: fuelPriority; from: 1; to: 10; value: Number(root.settingsData.fuelPriority || 3) }
                    Label { text: "MIN FREE CAPACITY"; color: Constants.textColor; font.family: Constants.technicalFont }
                    SpinBox { id: freeCapacity; from: 0; to: 1000; value: Number(root.settingsData.minimumFreeCapacity || 1) }
                    SpinBox { id: capacityPriority; from: 1; to: 10; value: Number(root.settingsData.inventoryPriority || 3) }
                }
            }

            Button { text: "SAVE AUTOMATION TARGETS"; Layout.alignment: Qt.AlignRight; onClicked: root.saveRequested(root.payload()) }
        }
    }
}
