pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

PanelFrame {
    id: root

    property string section: "FLEET"
    property var dashboardData: ({})
    property var availableProbes: []
    property int focusedProbeId: -1
    property double currentEpochMs: Date.now()
    signal probeSelected(int probeId)
    signal automationSettingsSaved(var settings)
    signal probeRoleAssigned(int probeId, string role)
    signal travelPreviewRequested(int x, int y, int z, string routeMode)
    signal travelExecuteRequested(bool riskAcknowledged)
    signal travelCancelRequested()
    signal sectorScanRequested(int x, int y, int z)
    signal neighboringSectorsScanRequested()
    signal autonomousTravelTargetRequested(int x, int y, int z)
    signal apiKeySaveRequested(string apiKey)
    signal apiKeyTestRequested()
    signal apiKeyRemoveRequested()
    signal onboardingResetRequested()
    signal executionPolicySaveRequested(var policy)
    signal automationCycleRequested()
    signal automationApprovalRequested(string fingerprint, bool riskAcknowledged)
    signal transportCycleSaveRequested(var plan)
    signal probeRenameRequested(string name)
    signal containerRenameRequested(string containerId, string label)
    signal storageRulesSaveRequested(string containerId, var rules)
    signal storageMoveRequested(var payload)
    signal jettisonRequested(string itemId, real amount, string containerId)
    signal inventoryMannyActionRequested(string action, string mannyId, var payload)
    signal logbookCreateRequested(string title, string content)
    signal logbookUpdateRequested(int pageId, string title, string content)
    signal logbookDeleteRequested(int pageId)
    signal autoLogbookChanged(bool enabled)
    signal logbookPageOpenRequested(int pageId)
    signal operatorManualRequested()
    signal changeLogRequested()
    signal updateCheckRequested()
    signal diagnosticLogsRequested()
    signal manualCraftRequested(string recipeId, string mannyId)

    function countdown(epochMs) {
        const seconds = Math.max(0, Math.floor((Number(epochMs) - currentEpochMs) / 1000));
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainder = seconds % 60;
        const pad = value => String(value).padStart(2, "0");
        return pad(hours) + ":" + pad(minutes) + ":" + pad(remainder);
    }

    Timer {
        interval: 1000
        running: root.visible && root.section === "PRODUCTION"
        repeat: true
        triggeredOnStart: true
        onTriggered: root.currentEpochMs = Date.now()
    }

    title: section

    function sectionRows() {
        if (section === "FLEET")
            return availableProbes.map(probe => ({
                        "title": probe.name + (probe.id === focusedProbeId ? "  ·  FOCUSED" : ""),
                        "detail": String(probe.model || "generic").split("_").join(" ").toUpperCase() + "  ·  " + String(probe.status || "unknown").toUpperCase() + "  ·  " + (probe.sectorLabel || "SECTOR UNKNOWN"),
                        "probeId": probe.id
                    }));
        if (section === "RESOURCES")
            return ((dashboardData.resourceLedger || {}).rows || []).map(item => ({
                        "title": item.title,
                        "detail": item.detail
                    })).concat(((dashboardData.resourceLedger || {}).notes || []).map(note => ({
                        "title": "API COVERAGE NOTE",
                        "detail": note
                    })));
        if (section === "MISSIONS")
            return (dashboardData.missions || []).map(item => ({
                        "title": item.displayText,
                        "detail": item.detailText
                    }));
        if (section === "PRODUCTION")
            return (dashboardData.production || []).map(item => ({
                        "title": item.displayText,
                        "detail": item.detailText,
                        "etaEpochMs": item.etaEpochMs || 0
                    }));
        if (section === "SAFETY")
            return (dashboardData.alerts || []).map(item => ({
                        "title": item.codeLabel,
                        "detail": item.summary
                    }));
        if (section === "LOGBOOK")
            return (dashboardData.events || []).map(item => ({
                        "title": String(item.domain || "EVENT").toUpperCase(),
                        "detail": item.observedAt || "Recorded event"
                    }));
        if (section === "RESEARCH")
            return [
                {
                    "title": "RESEARCH INTELLIGENCE",
                    "detail": "No account research endpoint is exposed by API v106. Discovered improvements remain available through probe inspection and safety context."
                }
            ];
        return [];
    }

    contentItem: Item {
        anchors.fill: parent

        GalaxyMap3D {
            anchors.fill: parent
            visible: root.section === "GALAXY MAP"
            galaxyData: root.dashboardData.galaxy || ({})
            focusedProbeId: root.focusedProbeId
            onScanRequested: (x, y, z) => root.sectorScanRequested(x, y, z)
        }

        AutomationSettings {
            anchors.fill: parent
            visible: root.section === "SETTINGS"
            settingsData: root.dashboardData.automation || ({})
            runtimeData: root.dashboardData.automationRuntime || ({})
            credentialData: root.dashboardData.credentials || ({})
            availableProbes: root.availableProbes
            focusedProbeId: root.focusedProbeId
            defaultProbeId: root.dashboardData.defaultProbeId === undefined ? -1 : Number(root.dashboardData.defaultProbeId)
            onSaveRequested: settings => root.automationSettingsSaved(settings)
            onRoleAssignmentRequested: (probeId, role) => root.probeRoleAssigned(probeId, role)
            onApiKeySaveRequested: apiKey => root.apiKeySaveRequested(apiKey)
            onApiKeyTestRequested: root.apiKeyTestRequested()
            onApiKeyRemoveRequested: root.apiKeyRemoveRequested()
            onOnboardingResetRequested: root.onboardingResetRequested()
            onExecutionPolicySaveRequested: policy => root.executionPolicySaveRequested(policy)
            onAutomationCycleRequested: root.automationCycleRequested()
            onAutomationApprovalRequested: (fingerprint, riskAcknowledged) => root.automationApprovalRequested(fingerprint, riskAcknowledged)
            onOperatorManualRequested: root.operatorManualRequested()
            onChangeLogRequested: root.changeLogRequested()
            onUpdateCheckRequested: root.updateCheckRequested()
            onDiagnosticLogsRequested: root.diagnosticLogsRequested()
        }

        NavigationControl {
            anchors.fill: parent
            visible: root.section === "NAVIGATION"
            navigationData: root.dashboardData.navigation || ({})
            travelPreview: root.dashboardData.travelPreview || ({})
            automationData: root.dashboardData.automation || ({})
            focusedProbe: root.dashboardData.focus || ({})
            onPreviewRequested: (x, y, z, routeMode) => root.travelPreviewRequested(x, y, z, routeMode)
            onExecuteRequested: riskAcknowledged => root.travelExecuteRequested(riskAcknowledged)
            onCancelMovementRequested: root.travelCancelRequested()
            onScanRequested: (x, y, z) => root.sectorScanRequested(x, y, z)
            onNeighborScanRequested: root.neighboringSectorsScanRequested()
            onAutonomousTargetRequested: (x, y, z) => root.autonomousTravelTargetRequested(x, y, z)
            onTransportCycleRequested: plan => root.transportCycleSaveRequested(plan)
        }

        ResourceWorkspace {
            anchors.fill: parent
            visible: root.section === "RESOURCES"
            ledgerData: root.dashboardData.resourceLedger || ({})
            inventoryData: root.dashboardData.inventoryManagement || ({})
            onProbeRenameRequested: name => root.probeRenameRequested(name)
            onContainerRenameRequested: (containerId, label) => root.containerRenameRequested(containerId, label)
            onStorageRulesSaveRequested: (containerId, rules) => root.storageRulesSaveRequested(containerId, rules)
            onStorageMoveRequested: payload => root.storageMoveRequested(payload)
            onJettisonRequested: (itemId, amount, containerId) => root.jettisonRequested(itemId, amount, containerId)
            onInventoryMannyActionRequested: (action, mannyId, payload) => root.inventoryMannyActionRequested(action, mannyId, payload)
        }

        FleetWorkspace {
            anchors.fill: parent
            visible: root.section === "FLEET"
            probes: root.availableProbes
            focusedProbeId: root.focusedProbeId
            onProbeSelected: probeId => root.probeSelected(probeId)
            onProbeRenameRequested: name => root.probeRenameRequested(name)
        }

        LogbookWorkspace {
            anchors.fill: parent
            visible: root.section === "LOGBOOK"
            logbookData: root.dashboardData.logbook || ({})
            onCreateRequested: (title, content) => root.logbookCreateRequested(title, content)
            onUpdateRequested: (pageId, title, content) => root.logbookUpdateRequested(pageId, title, content)
            onDeleteRequested: pageId => root.logbookDeleteRequested(pageId)
            onAutoLoggingChanged: enabled => root.autoLogbookChanged(enabled)
            onPageOpenRequested: pageId => root.logbookPageOpenRequested(pageId)
        }

        Column {
            visible: root.section !== "GALAXY MAP" && root.section !== "SETTINGS" && root.section !== "NAVIGATION" && root.section !== "RESOURCES" && root.section !== "FLEET" && root.section !== "LOGBOOK"
            anchors.fill: parent
            spacing: 12

            Label {
                width: parent.width
                text: root.section + " · LIVE ACCOUNT DATA"
                color: Constants.cyanColor
                font.family: Constants.technicalFont
                font.pixelSize: 14
            }

            Rectangle {
                visible: root.section === "PRODUCTION"
                width: parent.width
                height: visible ? manualBuildColumn.implicitHeight + 28 : 0
                color: Constants.raisedColor
                border.color: Constants.lineColor
                radius: 4

                ColumnLayout {
                    id: manualBuildColumn
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 14
                    spacing: 8
                    Label { text: "MANUAL BUILD ORDER"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
                    Label { Layout.fillWidth: true; text: "Start any API recipe without creating a persistent automation target. Manual orders still use the game's ingredient, storage-reservation, and Manny availability checks."; color: Constants.mutedTextColor; font.pixelSize: 13; wrapMode: Text.Wrap }
                    RowLayout {
                        Layout.fillWidth: true
                        ComboBox { id: manualRecipe; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: (root.dashboardData.crafting || {}).recipes || [] }
                        ComboBox { id: manualManny; Layout.preferredWidth: 260; textRole: "name"; valueRole: "id"; model: (root.dashboardData.crafting || {}).idleMannies || []; enabled: manualRecipe.currentValue && (((root.dashboardData.crafting || {}).recipes || [])[manualRecipe.currentIndex] || {}).craftableBy.indexOf("manny") >= 0 }
                        Button { text: "QUEUE BUILD"; enabled: manualRecipe.currentValue && (!manualManny.enabled || manualManny.currentValue); onClicked: root.manualCraftRequested(String(manualRecipe.currentValue), manualManny.enabled ? String(manualManny.currentValue) : "") }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Constants.lineColor
            }

            ScrollView {
                width: parent.width
                height: parent.height - 42 - (root.section === "PRODUCTION" ? manualBuildColumn.implicitHeight + 40 : 0)
                clip: true

                GridLayout {
                    id: sectionGrid
                    width: root.width
                    columns: root.width >= 1050 ? 2 : 1
                    columnSpacing: 18
                    rowSpacing: 18

                    Repeater {
                        model: root.sectionRows()
                        delegate: Rectangle {
                            id: sectionRow
                            required property var modelData
                            required property int index
                            Layout.preferredWidth: (root.width - (sectionGrid.columns - 1) * sectionGrid.columnSpacing) / sectionGrid.columns
                            Layout.minimumWidth: 420
                            implicitHeight: detailsColumn.implicitHeight + 40
                            color: rowMouse.containsMouse ? Constants.selectedColor : index % 2 ? Constants.panelColor : Constants.raisedColor
                            border.color: modelData.probeId === root.focusedProbeId ? Constants.cyanColor : Constants.lineColor
                            radius: 4

                            Column {
                            id: detailsColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 18
                            spacing: 10

                            Label {
                                width: parent.width
                                text: sectionRow.modelData.title || "No data"
                                color: Constants.textColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 17
                                font.bold: true
                                wrapMode: Text.Wrap
                            }
                            Label {
                                width: parent.width
                                text: sectionRow.modelData.detail || ""
                                color: Constants.mutedTextColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 15
                                lineHeight: 1.3
                                wrapMode: Text.Wrap
                            }
                            Label {
                                visible: Number(sectionRow.modelData.etaEpochMs || 0) > 0
                                width: parent.width
                                text: "COUNTDOWN  ·  " + root.countdown(sectionRow.modelData.etaEpochMs)
                                color: Constants.cyanColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 16
                                font.bold: true
                            }
                            }

                            MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: sectionRow.modelData.probeId !== undefined
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: root.probeSelected(Number(sectionRow.modelData.probeId))
                            }
                        }
                    }

                    Label {
                        visible: root.sectionRows().length === 0
                        Layout.columnSpan: sectionGrid.columns
                        Layout.alignment: Qt.AlignHCenter
                        text: "No live " + root.section.toLowerCase() + " records are currently available."
                        color: Constants.mutedTextColor
                        font.family: Constants.technicalFont
                        font.pixelSize: 14
                    }
                }
            }
        }
    }
}
