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

    signal craftRequested(string recipeId, string mannyId)
    signal repairRequested(string mannyId, real integrityPercent)
    signal upgradeRequested(string mannyId, string improvementId)
    signal miningRequested(string mannyId, var payload)
    signal containerRenameRequested(string containerId, string label)
    signal storageRulesSaveRequested(string containerId, var rules)
    signal storageMoveRequested(var payload)
    signal jettisonRequested(string itemId, real amount, string containerId)
    signal inventoryMannyActionRequested(string action, string mannyId, var payload)

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
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabs.currentIndex

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width - 20
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
                onStorageMoveRequested: payload => root.storageMoveRequested(payload)
                onJettisonRequested: (itemId, amount, containerId) => root.jettisonRequested(itemId, amount, containerId)
                onInventoryMannyActionRequested: (action, mannyId, payload) => root.inventoryMannyActionRequested(action, mannyId, payload)
            }
        }
    }
}
