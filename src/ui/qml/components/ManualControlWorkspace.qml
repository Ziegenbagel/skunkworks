pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var dashboardData: ({})
    property var probes: []
    property int focusedProbeId: -1
    readonly property bool manualCommandsEnabled: String((dashboardData.automationRuntime || {}).mode || "observe") !== "observe"
    readonly property var blueprintSharing: dashboardData.blueprintSharing || ({})

    signal craftRequested(string recipeId, string mannyId)
    signal repairRequested(string mannyId, real integrityPercent)
    signal upgradeRequested(string mannyId, string improvementId)
    signal miningRequested(string mannyId, var payload)
    signal probeAssemblyRequested(string mannyId, string model, var containerIds)
    signal containerRenameRequested(string containerId, string label)
    signal storageRulesSaveRequested(string containerId, var rules)
    signal craftingReservationsReassignRequested(string containerId)
    signal storageMoveRequested(var payload)
    signal jettisonRequested(string itemId, real amount, string containerId)
    signal inventoryMannyActionRequested(string action, string mannyId, var payload)
    signal asteroidTrajectoryRequested(string asteroidId, var payload)
    signal improvementBlueprintShareRequested(int networkId, string improvementId, int recipientProbeId)
    property var pendingAsteroidAction: ({})

    function readableDuration(secondsValue) {
        const seconds = Math.max(0, Math.round(Number(secondsValue || 0)));
        if (!seconds)
            return "TIME UNKNOWN";
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainder = seconds % 60;
        return (hours > 0 ? hours + " HR " : "") + minutes + " MIN " + remainder + " S";
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10
        Label {
            text: "MANUAL CONTROL · FOCUSED PROBE"
            color: Constants.cyanColor
            font.family: Constants.displayFont
            font.pixelSize: 19
            font.bold: true
        }
        Label {
            visible: !root.manualCommandsEnabled
            Layout.fillWidth: true
            text: "OBSERVE ONLY · MANUAL GAME COMMANDS ARE DISABLED. SELECT REQUIRE APPROVAL OR AUTOMATIC TO USE MANUAL CONTROL."
            color: Constants.warningColor
            font.family: Constants.technicalFont
            font.bold: true
            wrapMode: Text.Wrap
        }
        Label {
            Layout.fillWidth: true
            text: "One-time operator orders are kept separate from autonomous goals. Every live command still uses API validation, reservations, and Manny availability checks."
            color: Constants.mutedTextColor
            font.pixelSize: 14
            wrapMode: Text.Wrap
        }
        TabBar {
            id: tabs
            Layout.fillWidth: true
            TabButton { text: "PRODUCTION AND ASSEMBLY" }
            TabButton { text: "MANNY FIELD OPERATIONS" }
            TabButton { text: "CARGO AND TRANSFERS" }
            TabButton { text: "INFRASTRUCTURE AND NETWORKS" }
        }
        StackLayout {
            enabled: root.manualCommandsEnabled
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            Item {
                RowLayout {
                    anchors.fill: parent
                    spacing: 14
                    ScrollView {
                        id: buildControls
                        Layout.fillHeight: true
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        contentWidth: availableWidth
                        clip: true
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ColumnLayout {
                            width: buildControls.availableWidth - 12
                            spacing: 14
                    GroupBox {
                        title: "ONE-TIME MANUAL BUILD ORDER"
                        Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10
                            Label { Layout.fillWidth: true; text: "Start any currently exposed API recipe without creating a persistent automation target."; color: Constants.mutedTextColor; font.pixelSize: 14; wrapMode: Text.Wrap }
                            RowLayout {
                                Layout.fillWidth: true
                                ComboBox { id: recipe; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: (root.dashboardData.crafting || {}).recipes || [] }
                                ComboBox { id: craftManny; Layout.preferredWidth: 280; textRole: "name"; valueRole: "id"; model: (root.dashboardData.crafting || {}).idleMannies || []; enabled: recipe.currentIndex >= 0 && ((((root.dashboardData.crafting || {}).recipes || [])[recipe.currentIndex] || {}).craftableBy || []).indexOf("manny") >= 0 }
                                Button { text: "QUEUE BUILD"; enabled: recipe.currentIndex >= 0 && (!craftManny.enabled || craftManny.currentIndex >= 0); onClicked: root.craftRequested(String(recipe.currentValue), craftManny.enabled ? String(craftManny.currentValue) : "") }
                            }
                        }
                    }
                    GroupBox {
                        title: "MANUAL PROBE ASSEMBLY"
                        Layout.fillWidth: true
                        GridLayout {
                            anchors.fill: parent; columns: 4; columnSpacing: 12; rowSpacing: 10
                            Label { text: "MODEL"; color: Constants.cyanColor; font.bold: true }
                            ComboBox { id: assemblyModel; textRole: "name"; valueRole: "model"; model: (root.dashboardData.crafting || {}).probeAssemblies || []; Layout.fillWidth: true }
                            Label { text: "ASSEMBLY MANNY"; color: Constants.cyanColor; font.bold: true }
                            ComboBox { id: assemblyManny; textRole: "name"; valueRole: "id"; model: (root.dashboardData.crafting || {}).idleMannies || []; Layout.fillWidth: true }
                            Label { text: "EMPTY CONTAINER 1"; color: Constants.textColor }
                            ComboBox { id: assemblyContainerOne; textRole: "label"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).emptyAssemblyContainers || []; Layout.fillWidth: true }
                            Label { text: "EMPTY CONTAINER 2"; color: Constants.textColor }
                            ComboBox { id: assemblyContainerTwo; textRole: "label"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).emptyAssemblyContainers || []; Layout.fillWidth: true }
                            Label { Layout.columnSpan: 3; Layout.fillWidth: true; text: "Assembly takes three hours and consumes the selected two distinct empty additional containers plus every required model component shown above. It also consumes the selected assembly Manny from this probe and installs that Manny aboard the newly assembled probe. Recheck inventory before confirming."; color: Constants.warningColor; wrapMode: Text.Wrap }
                            Button { text: "REVIEW PROBE ASSEMBLY"; enabled: assemblyModel.count > 0 && assemblyManny.count > 0 && assemblyContainerOne.count >= 2 && String(assemblyContainerOne.currentValue) !== String(assemblyContainerTwo.currentValue); onClicked: assemblyConfirmation.open() }
                        }
                    }
                    GroupBox {
                        title: "PROBE ASSEMBLY REQUIREMENTS"
                        Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 10
                            Label {
                                Layout.fillWidth: true
                                text: "Crafted components consumed by each game probe model. New models appear here when their requirements are added to the assembly registry."
                                color: Constants.mutedTextColor; font.pixelSize: 14; wrapMode: Text.Wrap
                            }
                            Repeater {
                                model: (root.dashboardData.crafting || {}).probeAssemblies || []
                                delegate: Rectangle {
                                    id: assemblyCard
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 150
                                    color: Constants.raisedColor
                                    border.color: Constants.lineColor
                                    radius: 4
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 14; spacing: 7
                                        Label {
                                            Layout.fillWidth: true
                                            text: assemblyCard.modelData.name.toUpperCase()
                                            color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true
                                        }
                                        Label {
                                            Layout.fillWidth: true
                                            text: assemblyCard.modelData.assemblyAvailable
                                                ? "REQUIRED CRAFTED ITEMS"
                                                : "No operator-assembled component recipe is exposed for this model."
                                            color: assemblyCard.modelData.assemblyAvailable ? Constants.warningColor : Constants.mutedTextColor
                                            font.family: Constants.technicalFont; font.pixelSize: 12; wrapMode: Text.Wrap
                                        }
                                        Label {
                                            Layout.fillWidth: true; Layout.fillHeight: true
                                            visible: assemblyCard.modelData.assemblyAvailable
                                            text: (assemblyCard.modelData.components || []).map(function(item) {
                                                return String(item.quantity) + " × " + String(item.name).toUpperCase();
                                            }).join("  ·  ")
                                            color: Constants.textColor; font.pixelSize: 14; wrapMode: Text.Wrap
                                        }
                                    }
                                }
                            }
                        }
                    }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        Layout.fillHeight: true
                        spacing: 8
                        Label {
                            text: "CRAFTING REFERENCE · ALL AVAILABLE RECIPES"
                            color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 17; font.bold: true
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "Each recipe is expanded into the total raw resources required for one finished item. Crafted intermediates are shown only in the probe assembly reference."
                            color: Constants.mutedTextColor; font.pixelSize: 13; wrapMode: Text.Wrap
                        }
                        ListView {
                            id: recipeCatalog
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            spacing: 8
                            model: (root.dashboardData.crafting || {}).recipes || []
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                            delegate: Rectangle {
                                id: recipeCard
                                required property var modelData
                                width: recipeCatalog.width - (recipeCatalog.ScrollBar.vertical.visible ? 14 : 0)
                                height: 150
                                color: Constants.raisedColor
                                border.color: Constants.lineColor
                                radius: 4
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 13; spacing: 5
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Label { Layout.fillWidth: true; text: String(recipeCard.modelData.name || recipeCard.modelData.id).toUpperCase(); color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true; elide: Text.ElideRight }
                                        Label { text: root.readableDuration(recipeCard.modelData.durationSeconds); color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 12 }
                                    }
                                    Label { Layout.fillWidth: true; text: "FABRICATOR · " + (recipeCard.modelData.craftableBy || []).map(function(value) { return String(value).split("_").join(" ").toUpperCase(); }).join(" / "); color: Constants.mutedTextColor; font.pixelSize: 12; elide: Text.ElideRight }
                                    Label { Layout.fillWidth: true; text: recipeCard.modelData.description || "No description supplied by the game."; color: Constants.mutedTextColor; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                    Label {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        text: "TOTAL RAW RESOURCES · " + ((recipeCard.modelData.rawIngredients || []).length
                                            ? (recipeCard.modelData.rawIngredients || []).map(function(item) {
                                                return Number(item.quantity || 0) + " × " + String(item.name || item.type || "unknown").split("_").join(" ").toUpperCase();
                                            }).join("  ·  ")
                                            : "NO INPUTS")
                                        color: Constants.warningColor; font.pixelSize: 13; wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }

            FleetWorkspace {
                manualOnly: true
                probes: root.probes
                focusedProbeId: root.focusedProbeId
                probeData: root.dashboardData.probe || ({})
                idleMannies: (root.dashboardData.inventoryManagement || {}).idleMannies || []
                improvements: root.dashboardData.probeImprovements || []
                miningTargets: (root.dashboardData.inventoryManagement || {}).miningTargets || []
                detachedContainers: (root.dashboardData.inventoryManagement || {}).detachedContainers || []
                sameSectorProbes: (root.dashboardData.inventoryManagement || {}).sameSectorProbes || []
                allMannies: (root.dashboardData.inventoryManagement || {}).mannies || []
                deuterium: Number((root.dashboardData.inventoryManagement || {}).deuterium || 0)
                maximumMiningOrderAmount: Number((root.dashboardData.automation || {}).maximumMiningOrderAmount || 0.55)
                onRepairRequested: (mannyId, integrityPercent) => root.repairRequested(mannyId, integrityPercent)
                onUpgradeRequested: (mannyId, improvementId) => root.upgradeRequested(mannyId, improvementId)
                onMiningRequested: (mannyId, payload) => root.miningRequested(mannyId, payload)
                onInventoryMannyActionRequested: (action, mannyId, payload) => root.inventoryMannyActionRequested(action, mannyId, payload)
            }

            InventoryWorkspace {
                inventoryData: root.dashboardData.inventoryManagement || ({})
                onContainerRenameRequested: (containerId, label) => root.containerRenameRequested(containerId, label)
                onStorageRulesSaveRequested: (containerId, rules) => root.storageRulesSaveRequested(containerId, rules)
                onCraftingReservationsReassignRequested: containerId => root.craftingReservationsReassignRequested(containerId)
                onStorageMoveRequested: payload => root.storageMoveRequested(payload)
                onJettisonRequested: (itemId, amount, containerId) => root.jettisonRequested(itemId, amount, containerId)
                onInventoryMannyActionRequested: (action, mannyId, payload) => root.inventoryMannyActionRequested(action, mannyId, payload)
            }

            Item {
                ScrollView {
                    id: asteroidControls
                    anchors.fill: parent
                    contentWidth: availableWidth
                    clip: true
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                    ColumnLayout {
                        width: Math.max(1, asteroidControls.availableWidth - 12)
                        spacing: 14

                        Label { Layout.fillWidth: true; text: "MOTORIZED ASTEROID OPERATIONS · API v112"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
                        Label { Layout.fillWidth: true; text: "These are direct one-time game commands. Motorization and refueling consume resources immediately. Launching consumes the asteroid's full binary fuel tank and cannot be cancelled through the current API."; color: Constants.warningColor; font.pixelSize: 14; wrapMode: Text.Wrap }

                        GroupBox {
                            title: "INSTALL ASTEROID PROPULSION"
                            Layout.fillWidth: true
                            GridLayout {
                                anchors.fill: parent; columns: 3; columnSpacing: 12; rowSpacing: 10
                                Label { text: "IDLE MANNY"; color: Constants.cyanColor; font.bold: true }
                                ComboBox { id: motorizeManny; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).idleMannies || [] }
                                Item { Layout.preferredWidth: 1 }
                                Label { text: "ASTEROID"; color: Constants.cyanColor; font.bold: true }
                                ComboBox { id: motorizeTarget; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).motorizationTargets || [] }
                                Button { text: "REVIEW INSTALLATION"; enabled: Boolean((root.dashboardData.inventoryManagement || {}).asteroidMotorizationAvailable) && motorizeManny.count > 0 && motorizeTarget.count > 0; onClicked: { root.pendingAsteroidAction = {"action":"motorize-asteroid", "mannyId":String(motorizeManny.currentValue), "objectId":String(motorizeTarget.currentValue)}; asteroidTaskConfirmation.open(); } }
                                Label { Layout.columnSpan: 3; Layout.fillWidth: true; text: "Requires Distributed Thrust Anchoring. The game consumes 1 Deuterium Engine, 4 Steel Bars, 2 Steel Plates, and 0.2 ECE Deuterium, then sends the Manny out to install propulsion."; color: Constants.mutedTextColor; wrapMode: Text.Wrap }
                                Label { visible: !Boolean((root.dashboardData.inventoryManagement || {}).asteroidMotorizationAvailable); Layout.columnSpan: 3; Layout.fillWidth: true; text: "LOCKED · DISTRIBUTED THRUST ANCHORING IS NOT CURRENTLY AVAILABLE TO THIS PROBE OWNER."; color: Constants.warningColor; font.bold: true; wrapMode: Text.Wrap }
                            }
                        }

                        GroupBox {
                            title: "REFUEL MOTORIZED ASTEROID"
                            Layout.fillWidth: true
                            RowLayout {
                                anchors.fill: parent; spacing: 12
                                ComboBox { id: refuelManny; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).idleMannies || [] }
                                ComboBox { id: refuelTarget; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).refuelAsteroidTargets || [] }
                                Button { text: "REVIEW REFUEL"; enabled: refuelManny.count > 0 && refuelTarget.count > 0; onClicked: { root.pendingAsteroidAction = {"action":"refuel-motorized-asteroid", "mannyId":String(refuelManny.currentValue), "objectId":String(refuelTarget.currentValue)}; asteroidTaskConfirmation.open(); } }
                            }
                        }

                        GroupBox {
                            title: "LAUNCH MOTORIZED ASTEROID"
                            Layout.fillWidth: true
                            GridLayout {
                                anchors.fill: parent; columns: 4; columnSpacing: 12; rowSpacing: 10
                                Label { text: "ASTEROID"; color: Constants.cyanColor; font.bold: true }
                                ComboBox { id: launchAsteroid; Layout.fillWidth: true; Layout.columnSpan: 3; textRole: "name"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).launchableAsteroids || [] }
                                Label { text: "MODE"; color: Constants.cyanColor; font.bold: true }
                                ComboBox { id: launchMode; textRole: "text"; valueRole: "value"; model: [{"text":"MOVE TO NEIGHBORING SECTOR", "value":"sector_transfer"}, {"text":"IMPACT LOCAL OBJECT", "value":"system_impact"}]; Layout.fillWidth: true }
                                Label { visible: launchMode.currentValue === "system_impact"; text: "TARGET"; color: Constants.criticalColor; font.bold: true }
                                ComboBox { id: impactTarget; visible: launchMode.currentValue === "system_impact"; Layout.fillWidth: true; textRole: "label"; valueRole: "id"; model: ((root.dashboardData.inventoryManagement || {}).asteroidImpactTargets || []).filter(function(item) { return String(item.id) !== String(launchAsteroid.currentValue); }) }
                                Label { visible: launchMode.currentValue === "system_impact"; text: "TARGET SPEED"; color: Constants.criticalColor; font.bold: true }
                                RowLayout { visible: launchMode.currentValue === "system_impact"; Layout.columnSpan: 3; SpinBox { id: impactSpeed; from: 1; to: 50; value: 10; editable: true } Label { text: (Number(impactSpeed.value) / 100).toFixed(2) + " c"; color: Constants.textColor } }
                                Label { visible: launchMode.currentValue === "sector_transfer"; text: "NEIGHBOR FCC"; color: Constants.cyanColor; font.bold: true }
                                RowLayout { visible: launchMode.currentValue === "sector_transfer"; Layout.columnSpan: 3; Label { text: "X" } SpinBox { id: transferX; from: -1000000; to: 1000000; editable: true } Label { text: "Y" } SpinBox { id: transferY; from: -1000000; to: 1000000; editable: true } Label { text: "Z" } SpinBox { id: transferZ; from: -1000000; to: 1000000; editable: true } }
                                Label { Layout.columnSpan: 3; Layout.fillWidth: true; text: launchMode.currentValue === "system_impact" ? "DANGER: this deliberately accelerates the asteroid toward the selected local object. The game may report damage, destruction, fragmentation, a miss, or no effect; Skunkworks cannot predict the result." : "The destination must be a directly neighboring valid FCC sector. Transfer advances one sector per 24 hours and may end in capture, loss, or another terminal outcome."; color: launchMode.currentValue === "system_impact" ? Constants.criticalColor : Constants.warningColor; font.bold: true; wrapMode: Text.Wrap }
                                Button { text: "REVIEW LAUNCH"; enabled: launchAsteroid.count > 0 && (launchMode.currentValue !== "system_impact" || impactTarget.count > 0); onClicked: asteroidLaunchConfirmation.open() }
                            }
                        }

                        GroupBox {
                            title: "SCULPT ANATIFORM ASTEROID · API v115"
                            Layout.fillWidth: true
                            ColumnLayout {
                                anchors.fill: parent; spacing: 8
                                RowLayout {
                                    Layout.fillWidth: true; spacing: 12
                                    ComboBox { id: sculptManny; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).idleMannies || [] }
                                    ComboBox { id: sculptTarget; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: (root.dashboardData.inventoryManagement || {}).sculptableAsteroids || [] }
                                    Button { text: "REVIEW TWO-DAY SCULPT"; enabled: Boolean((root.dashboardData.inventoryManagement || {}).anatiformSculptingAvailable) && sculptManny.count > 0 && sculptTarget.count > 0; onClicked: { root.pendingAsteroidAction = {"action":"sculpt-duck-asteroid", "mannyId":String(sculptManny.currentValue), "objectId":String(sculptTarget.currentValue)}; asteroidTaskConfirmation.open(); } }
                                }
                                Label { Layout.fillWidth: true; visible: !Boolean((root.dashboardData.inventoryManagement || {}).anatiformSculptingAvailable); text: "LOCKED · ANATIFORM ASTEROID SCULPTING BLUEPRINT IS NOT KNOWN."; color: Constants.warningColor; font.bold: true; wrapMode: Text.Wrap }
                            }
                        }

                        GroupBox {
                            title: "DETECTED ACTIVE TRAJECTORIES"
                            Layout.fillWidth: true
                            ColumnLayout {
                                anchors.fill: parent
                                Label { visible: ((root.dashboardData.inventoryManagement || {}).asteroidTrajectories || []).length === 0; text: "No active motorized-asteroid trajectory is visible in the current detailed sector scan."; color: Constants.mutedTextColor; wrapMode: Text.Wrap }
                                Repeater {
                                    model: (root.dashboardData.inventoryManagement || {}).asteroidTrajectories || []
                                    delegate: Label { required property var modelData; Layout.fillWidth: true; text: String(modelData.id || "TRAJECTORY") + " · " + String(modelData.mode || "unknown").split("_").join(" ").toUpperCase() + " · " + String(modelData.status || "unknown").split("_").join(" ").toUpperCase() + (modelData.estimatedCompletionAt ? " · ETA " + String(modelData.estimatedCompletionAt) : ""); color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                                }
                            }
                        }

                        Label { Layout.fillWidth: true; text: "SHARE IMPROVEMENT BLUEPRINT · API v113"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
                        Label { Layout.fillWidth: true; text: "Copy one blueprint you know to the owner of another player's probe. Both the focused probe and recipient must share coverage from the selected active SCUT network. Same-sector proximity alone is not sufficient."; color: Constants.mutedTextColor; font.pixelSize: 14; wrapMode: Text.Wrap }
                        GroupBox {
                            title: "BLUEPRINT TRANSFER"
                            Layout.fillWidth: true
                            GridLayout {
                                anchors.fill: parent; columns: 3; columnSpacing: 12; rowSpacing: 10
                                Label { text: "SCUT NETWORK"; color: Constants.cyanColor; font.bold: true }
                                ComboBox { id: blueprintNetwork; Layout.fillWidth: true; Layout.columnSpan: 2; textRole: "name"; valueRole: "id"; model: root.blueprintSharing.networks || [] }
                                Label { text: "KNOWN BLUEPRINT"; color: Constants.cyanColor; font.bold: true }
                                ComboBox { id: sharedBlueprint; Layout.fillWidth: true; Layout.columnSpan: 2; textRole: "name"; valueRole: "id"; model: root.blueprintSharing.blueprints || [] }
                                Label { text: "RECIPIENT PROBE"; color: Constants.cyanColor; font.bold: true }
                                ComboBox { id: blueprintRecipient; Layout.fillWidth: true; Layout.columnSpan: 2; textRole: "name"; valueRole: "id"; model: (((root.blueprintSharing.networks || [])[blueprintNetwork.currentIndex] || {}).recipients || []) }
                                Label { Layout.columnSpan: 2; Layout.fillWidth: true; text: "Sharing is idempotent: repeating a completed transfer does not duplicate the recipient's persistent blueprint-shared alert."; color: Constants.warningColor; wrapMode: Text.Wrap }
                                Button { text: "REVIEW BLUEPRINT SHARE"; enabled: blueprintNetwork.count > 0 && sharedBlueprint.count > 0 && blueprintRecipient.count > 0; onClicked: blueprintShareConfirmation.open() }
                            }
                        }
                        Label { visible: (root.blueprintSharing.networks || []).length === 0; Layout.fillWidth: true; text: "NO ACTIVE SCUT NETWORK DETAILS ARE AVAILABLE FOR THE FOCUSED PROBE."; color: Constants.warningColor; font.bold: true; wrapMode: Text.Wrap }
                        Label { visible: (root.blueprintSharing.blueprints || []).length === 0; Layout.fillWidth: true; text: "NO KNOWN IMPROVEMENT BLUEPRINTS ARE AVAILABLE TO SHARE."; color: Constants.warningColor; font.bold: true; wrapMode: Text.Wrap }
                    }
                }
            }
        }
    }

    Dialog {
        id: assemblyConfirmation; anchors.centerIn: parent; modal: true
        title: "CONFIRM PROBE ASSEMBLY"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.probeAssemblyRequested(String(assemblyManny.currentValue), String(assemblyModel.currentValue), [String(assemblyContainerOne.currentValue), String(assemblyContainerTwo.currentValue)])
        Label { width: 600; text: "This sends a live three-hour assembly order and consumes the two selected empty containers, all required crafted components, and the selected assembly Manny. That Manny is installed aboard the newly assembled probe and will no longer remain on the current probe. Cancelling later leaves consumed ingredients drifting in the assembly sector."; color: Constants.criticalColor; wrapMode: Text.Wrap }
    }
    Dialog {
        id: asteroidTaskConfirmation; anchors.centerIn: parent; modal: true
        title: root.pendingAsteroidAction.action === "motorize-asteroid" ? "CONFIRM ASTEROID MOTORIZATION" : root.pendingAsteroidAction.action === "sculpt-duck-asteroid" ? "CONFIRM TWO-DAY ANATIFORM SCULPT" : "CONFIRM ASTEROID REFUEL"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.inventoryMannyActionRequested(String(root.pendingAsteroidAction.action), String(root.pendingAsteroidAction.mannyId), {"objectId":String(root.pendingAsteroidAction.objectId)})
        Label { width: 620; text: root.pendingAsteroidAction.action === "motorize-asteroid" ? "This consumes the documented propulsion components and 0.2 ECE Deuterium, then sends the selected Manny outside the probe." : root.pendingAsteroidAction.action === "sculpt-duck-asteroid" ? "This assigns the selected onboard Manny for exactly two days. The asteroid changes only at completion; recalling the Manny early leaves it ordinary." : "This immediately consumes 0.2 ECE Deuterium and sends the selected Manny to refill the asteroid's binary motor tank."; color: Constants.warningColor; wrapMode: Text.Wrap }
    }
    Dialog {
        id: asteroidLaunchConfirmation; anchors.centerIn: parent; modal: true
        title: launchMode.currentValue === "system_impact" ? "CONFIRM DESTRUCTIVE ASTEROID IMPACT" : "CONFIRM ASTEROID SECTOR TRANSFER"
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.asteroidTrajectoryRequested(String(launchAsteroid.currentValue), launchMode.currentValue === "system_impact" ? {"mode":"system_impact", "targetObjectId":String(impactTarget.currentValue), "targetSpeedC":Number(impactSpeed.value) / 100} : {"mode":"sector_transfer", "target":{"x":transferX.value, "y":transferY.value, "z":transferZ.value}})
        Label { width: 660; text: launchMode.currentValue === "system_impact" ? "IRREVERSIBLE: launch this asteroid toward the selected local object. The outcome is resolved by the game and may damage or destroy assets. Skunkworks cannot cancel the trajectory or predict its result." : "IRREVERSIBLE: consume the asteroid's full fuel tank and begin transfer to the entered neighboring FCC sector. Confirm the coordinates carefully."; color: Constants.criticalColor; font.bold: true; wrapMode: Text.Wrap }
    }
    Dialog {
        id: blueprintShareConfirmation; anchors.centerIn: parent; modal: true
        title: "CONFIRM SCUT BLUEPRINT SHARE"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.improvementBlueprintShareRequested(Number(blueprintNetwork.currentValue), String(sharedBlueprint.currentValue), Number(blueprintRecipient.currentValue))
        Label { width: 640; text: "This copies the selected blueprint to the player who owns the recipient probe. Your blueprint is retained. The recipient gains it account-wide and receives a persistent notification."; color: Constants.warningColor; wrapMode: Text.Wrap }
    }
}
