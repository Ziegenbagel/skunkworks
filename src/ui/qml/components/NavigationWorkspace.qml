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
    signal probeSelected(int probeId)
    signal automationSettingsSaved(var settings)
    signal probeRoleAssigned(int probeId, string role)
    signal travelPreviewRequested(int x, int y, int z, string routeMode)
    signal travelExecuteRequested(bool riskAcknowledged)
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
    signal logbookCreateRequested(string title, string content)
    signal logbookUpdateRequested(int pageId, string title, string content)
    signal logbookDeleteRequested(int pageId)
    signal autoLogbookChanged(bool enabled)
    signal logbookPageOpenRequested(int pageId)

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
                        "detail": item.detailText
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
                    "detail": "No account research endpoint is exposed by API v104. Discovered improvements remain available through probe inspection and safety context."
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
            onScanRequested: (x, y, z) => root.sectorScanRequested(x, y, z)
        }

        AutomationSettings {
            anchors.fill: parent
            visible: root.section === "SETTINGS"
            settingsData: root.dashboardData.automation || ({})
            runtimeData: root.dashboardData.automationRuntime || ({})
            credentialData: root.dashboardData.credentials || ({})
            availableProbes: root.availableProbes
            onSaveRequested: settings => root.automationSettingsSaved(settings)
            onRoleAssignmentRequested: (probeId, role) => root.probeRoleAssigned(probeId, role)
            onApiKeySaveRequested: apiKey => root.apiKeySaveRequested(apiKey)
            onApiKeyTestRequested: root.apiKeyTestRequested()
            onApiKeyRemoveRequested: root.apiKeyRemoveRequested()
            onOnboardingResetRequested: root.onboardingResetRequested()
            onExecutionPolicySaveRequested: policy => root.executionPolicySaveRequested(policy)
            onAutomationCycleRequested: root.automationCycleRequested()
            onAutomationApprovalRequested: (fingerprint, riskAcknowledged) => root.automationApprovalRequested(fingerprint, riskAcknowledged)
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
                width: parent.width
                height: 1
                color: Constants.lineColor
            }

            ScrollView {
                width: parent.width
                height: parent.height - 42
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
