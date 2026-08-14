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
            TabButton { text: "CRAFTING" }
            TabButton { text: "MINING & MAINTENANCE" }
            TabButton { text: "TRANSFERS & CONTAINERS" }
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
                            Label { Layout.columnSpan: 3; Layout.fillWidth: true; text: "Assembly takes three hours and consumes the selected two distinct empty additional containers plus every required model component shown above. Recheck inventory before confirming."; color: Constants.warningColor; wrapMode: Text.Wrap }
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
                maximumMiningOrderAmount: Number((root.dashboardData.automation || {}).maximumMiningOrderAmount || 0.55)
                onRepairRequested: (mannyId, integrityPercent) => root.repairRequested(mannyId, integrityPercent)
                onUpgradeRequested: (mannyId, improvementId) => root.upgradeRequested(mannyId, improvementId)
                onMiningRequested: (mannyId, payload) => root.miningRequested(mannyId, payload)
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
        }
    }

    Dialog {
        id: assemblyConfirmation; anchors.centerIn: parent; modal: true
        title: "CONFIRM PROBE ASSEMBLY"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.probeAssemblyRequested(String(assemblyManny.currentValue), String(assemblyModel.currentValue), [String(assemblyContainerOne.currentValue), String(assemblyContainerTwo.currentValue)])
        Label { width: 600; text: "This sends a live three-hour assembly order and consumes the two selected empty containers and all required crafted components. Cancelling later leaves consumed ingredients drifting in the assembly sector."; color: Constants.criticalColor; wrapMode: Text.Wrap }
    }
}
