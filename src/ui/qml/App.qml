import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    property var backend: null
    readonly property bool hasLiveSnapshot: window.backend !== null
        && Object.keys(window.backend.dashboard || ({})).length > 0
    width: Constants.width
    height: Constants.height
    minimumWidth: Constants.minimumWidth
    minimumHeight: Constants.minimumHeight
    visible: true
    title: "Skunkworks Mission Control"
    color: Constants.voidColor

    Component.onCompleted: AudioManager.startMusic()
    onClosing: function(close) {
        if (window.backend && !window.backend.shuttingDown) {
            close.accepted = false;
            window.backend.shutdown();
        }
    }

    MissionControlScreen {
        id: missionControl
        anchors.fill: parent
        liveMode: window.backend !== null
        dashboardData: window.backend ? window.backend.dashboard : ({})
        availableProbes: window.backend ? window.backend.availableProbes : previewProbes
        focusedProbeId: window.backend ? window.backend.focusedProbeId : availableProbes[0].id
        refreshing: window.backend ? window.backend.refreshing : false
        connectionError: window.backend ? window.backend.error : ""
        emergencyStopActive: window.backend ? window.backend.emergencyStopActive : false
        visible: !startupOverlay.visible
    }

    Rectangle {
        id: staleDataBanner
        z: 850
        visible: window.backend !== null && window.backend.error && window.hasLiveSnapshot
        anchors.top: parent.top
        anchors.topMargin: 88
        anchors.horizontalCenter: parent.horizontalCenter
        width: Math.min(parent.width - 48, 980)
        height: 74
        color: "#301b08"
        border.color: Constants.warningColor
        border.width: 2
        radius: 4

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 14
            Label {
                text: "⚠"
                color: Constants.warningColor
                font.pixelSize: 28
            }
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Label {
                    text: "LIVE LINK INTERRUPTED · SHOWING LAST SUCCESSFUL SNAPSHOT"
                    color: Constants.warningColor
                    font.family: Constants.technicalFont
                    font.bold: true
                    font.pixelSize: 14
                }
                Label {
                    Layout.fillWidth: true
                    text: window.backend ? window.backend.error : ""
                    color: Constants.textColor
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }
            }
            Button {
                text: window.backend && window.backend.refreshing ? "RETRYING…" : "RETRY NOW"
                enabled: window.backend && !window.backend.refreshing
                onClicked: window.backend.refresh()
            }
        }
    }

    Rectangle {
        id: unavailableOverlay
        anchors.fill: parent
        z: 875
        visible: window.backend !== null && window.backend.error && !window.hasLiveSnapshot
        color: Constants.voidColor

        ColumnLayout {
            anchors.centerIn: parent
            width: Math.min(parent.width - 80, 760)
            spacing: 18
            Label {
                Layout.alignment: Qt.AlignHCenter
                text: "LIVE FLEET DATA UNAVAILABLE"
                color: Constants.criticalColor
                font.family: Constants.displayFont
                font.pixelSize: 30
                font.bold: true
                font.letterSpacing: 2
            }
            Label {
                Layout.alignment: Qt.AlignHCenter
                text: "Skunkworks did not load concept or sample fleet values.\nNo live account snapshot is currently available."
                horizontalAlignment: Text.AlignHCenter
                color: Constants.textColor
                font.pixelSize: 15
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(88, unavailableMessage.implicitHeight + 32)
                color: Constants.panelColor
                border.color: Constants.criticalColor
                radius: 4
                Label {
                    id: unavailableMessage
                    anchors.fill: parent
                    anchors.margins: 16
                    text: window.backend ? window.backend.error : ""
                    color: Constants.mutedTextColor
                    font.family: Constants.technicalFont
                    font.pixelSize: 12
                    wrapMode: Text.Wrap
                    verticalAlignment: Text.AlignVCenter
                }
            }
            Label {
                Layout.alignment: Qt.AlignHCenter
                text: "The game service may be temporarily unavailable. Existing local history and settings have not been erased."
                color: Constants.warningColor
                font.pixelSize: 12
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                Layout.maximumWidth: 680
            }
            Button {
                Layout.alignment: Qt.AlignHCenter
                text: window.backend && window.backend.refreshing ? "RETRYING LIVE CONNECTION…" : "RETRY LIVE CONNECTION"
                enabled: window.backend && !window.backend.refreshing
                onClicked: window.backend.refresh()
            }
        }
    }

    Rectangle {
        id: startupOverlay
        anchors.fill: parent
        z: 900
        visible: window.backend !== null && window.backend.startupLoading
        color: Constants.voidColor

        Column {
            anchors.centerIn: parent
            spacing: 22

            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "S K U N K W O R K S"
                color: Constants.textColor
                font.family: Constants.displayFont
                font.pixelSize: 38
                font.bold: true
            }
            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "AUTONOMOUS EXPLORATION & FLEET OPERATIONS"
                color: Constants.cyanColor
                font.family: Constants.technicalFont
                font.pixelSize: 14
                font.letterSpacing: 2
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 360
                height: 2
                color: Constants.lineColor
                Rectangle {
                    id: loadingSweep
                    width: 90
                    height: parent.height
                    color: Constants.cyanColor
                    SequentialAnimation on x {
                        loops: Animation.Infinite
                        NumberAnimation { from: 0; to: 270; duration: 900; easing.type: Easing.InOutQuad }
                        NumberAnimation { from: 270; to: 0; duration: 900; easing.type: Easing.InOutQuad }
                    }
                }
            }
            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: (window.backend ? window.backend.loadingProgress : 0) + "%"
                color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 18; font.bold: true
            }
            Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: String(window.backend ? window.backend.loadingStatus : "LOADING LIVE FLEET DATA").toUpperCase()
                color: Constants.mutedTextColor
                font.family: Constants.technicalFont
                font.pixelSize: 12
            }
        }
    }

    FirstLaunchWizard {
        id: firstLaunchWizard
        anchors.fill: parent
        z: 1000
        visible: window.backend ? window.backend.onboardingRequired : false
        credentialConfigured: window.backend ? window.backend.credentialConfigured : false
        credentialMessage: window.backend ? window.backend.credentialMessage : ""
        onApiKeySaveRequested: apiKey => { if (window.backend) window.backend.saveApiKey(apiKey); }
        onApiKeyTestRequested: { if (window.backend) window.backend.testApiKey(); }
        onFinishRequested: { if (window.backend) window.backend.completeOnboarding(); }
    }

    Connections {
        target: window.backend
        ignoreUnknownSignals: true

        function onStartupLoadingChanged() {
            if (window.backend && !window.backend.startupLoading)
                AudioManager.play("load");
        }
        function onErrorChanged() {
            if (window.backend && window.backend.error)
                AudioManager.play("error");
        }
    }

    Connections {
        target: missionControl.probeSelectorControl

        function onProbeSelected(probeId) {
            AudioManager.play("select");
            if (window.backend)
                window.backend.selectProbe(probeId);
            else
                missionControl.focusedProbeId = probeId;
        }

        function onRefreshRequested() {
            AudioManager.play("press");
            if (window.backend)
                window.backend.refresh();
        }
    }

    Connections {
        target: missionControl.emergencyStopControl

        function onClicked() {
            AudioManager.play(window.backend && window.backend.emergencyStopActive ? "confirm" : "warning");
            if (window.backend)
                window.backend.setEmergencyStop(!window.backend.emergencyStopActive);
        }
    }

    Connections {
        target: missionControl.alertsButtonControl

        function onClicked() {
            AudioManager.play("navigate");
            missionControl.currentNavigation = "SAFETY";
        }
    }

    Connections {
        target: missionControl.navigationBarControl

        function onSectionSelected(section) {
            AudioManager.play("navigate");
            missionControl.currentNavigation = section;
        }
    }

    Connections {
        target: missionControl.navigationWorkspaceControl

        function onProbeSelected(probeId) {
            AudioManager.play("select");
            if (window.backend)
                window.backend.selectProbe(probeId);
            else
                missionControl.focusedProbeId = probeId;
        }

        function onAutomationSettingsSaved(settings) {
            AudioManager.play("save");
            if (window.backend)
                window.backend.saveAutomationSettings(settings);
        }

        function onShutdownRequested() {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.shutdown();
            else
                Qt.quit();
        }

        function onFleetNamingRequested(policy, applyExisting) {
            AudioManager.play("save");
            if (window.backend)
                window.backend.saveFleetNamingPolicy(policy, applyExisting);
        }

        function onManualCraftRequested(recipeId, mannyId) {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.queueManualCraft(recipeId, mannyId);
        }

        function onManualRepairRequested(mannyId, integrityPercent) {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.queueManualRepair(mannyId, integrityPercent);
        }

        function onManualUpgradeRequested(mannyId, improvementId) {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.queueManualUpgrade(mannyId, improvementId);
        }

        function onManualMiningRequested(mannyId, payload) {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.runInventoryMannyAction("mine", mannyId, payload);
        }

        function onMannyCancelRequested(mannyId) {
            AudioManager.play("warning");
            if (window.backend)
                window.backend.runInventoryMannyAction("recall", mannyId, ({}));
        }

        function onDiagnosticLogsRequested() {
            AudioManager.play("press");
            if (window.backend)
                window.backend.openDiagnosticLogs();
        }

        function onProbeRoleAssigned(probeId, role) {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.assignProbeRole(probeId, role);
        }
        function onProbeRoleSettingsSaved(probeId, settings) {
            if (window.backend)
                window.backend.saveProbeRoleSettings(probeId, settings);
        }

        function onTravelPreviewRequested(x, y, z, routeMode) {
            AudioManager.play("press");
            if (window.backend)
                window.backend.previewTravel(x, y, z, routeMode);
        }

        function onTravelExecuteRequested(riskAcknowledged) {
            AudioManager.play("confirm");
            if (window.backend)
                window.backend.executeTravel(riskAcknowledged);
        }

        function onTravelCancelRequested() {
            AudioManager.play("warning");
            if (window.backend)
                window.backend.cancelTravel();
        }

        function onSectorScanRequested(x, y, z) {
            AudioManager.play("press");
            if (window.backend)
                window.backend.scanSector(x, y, z);
        }

        function onNeighboringSectorsScanRequested() {
            AudioManager.play("press");
            if (window.backend)
                window.backend.scanNeighboringSectors();
        }

        function onAutonomousTravelTargetRequested(x, y, z, routeMode, riskAcknowledged, scutExitAcknowledged) {
            AudioManager.play("save");
            if (window.backend)
                window.backend.setAutonomousTravelTarget(x, y, z, routeMode, riskAcknowledged, scutExitAcknowledged);
        }

        function onAutonomousTravelTargetCancelRequested() {
            AudioManager.play("warning");
            if (window.backend)
                window.backend.cancelAutonomousTravelTarget();
        }

        function onApiKeySaveRequested(apiKey) {
            AudioManager.play("save");
            if (window.backend) window.backend.saveApiKey(apiKey);
        }

        function onApiKeyTestRequested() {
            AudioManager.play("press");
            if (window.backend) window.backend.testApiKey();
        }

        function onApiKeyRemoveRequested() {
            AudioManager.play("warning");
            if (window.backend) window.backend.removeApiKey();
        }

        function onOnboardingResetRequested() {
            AudioManager.play("press");
            if (window.backend) window.backend.resetOnboarding();
        }

        function onExecutionPolicySaveRequested(policy) {
            AudioManager.play("save");
            if (window.backend) window.backend.saveExecutionPolicy(policy);
        }

        function onAutomationCycleRequested() {
            AudioManager.play("confirm");
            if (window.backend) window.backend.runAutomationCycle();
        }

        function onAutomationApprovalRequested(fingerprint, riskAcknowledged) {
            AudioManager.play("confirm");
            if (window.backend) window.backend.approveAutomationCommand(fingerprint, riskAcknowledged);
        }

        function onTransportCycleSaveRequested(plan) {
            AudioManager.play("save");
            if (window.backend) window.backend.saveTransportCycle(plan);
        }

        function onTransportCycleStartRequested(operationId) {
            AudioManager.play("confirm");
            if (window.backend) window.backend.startTransportCycle(operationId);
        }

        function onTransportCyclePauseRequested(operationId) {
            AudioManager.play("cancel");
            if (window.backend) window.backend.pauseTransportCycle(operationId);
        }

        function onTransportCycleDeleteRequested(operationId) {
            AudioManager.play("cancel");
            if (window.backend) window.backend.deleteTransportCycle(operationId);
        }

        function onProbeRenameRequested(name) {
            AudioManager.play("save");
            if (window.backend) window.backend.renameFocusedProbe(name);
        }

        function onMannyRenameRequested(mannyId, name) {
            AudioManager.play("save");
            if (window.backend)
                window.backend.renameManny(mannyId, name);
        }

        function onContainerRenameRequested(containerId, label) {
            AudioManager.play("save");
            if (window.backend) window.backend.renameStorageContainer(containerId, label);
        }

        function onStorageRulesSaveRequested(containerId, rules) {
            AudioManager.play("save");
            if (window.backend) window.backend.saveStorageRules(containerId, rules);
        }

        function onStorageMoveRequested(payload) {
            AudioManager.play("confirm");
            if (window.backend) window.backend.moveStorage(payload);
        }

        function onJettisonRequested(itemId, amount, containerId) {
            AudioManager.play("warning");
            if (window.backend) window.backend.jettisonInventory(itemId, amount, containerId);
        }

        function onInventoryMannyActionRequested(action, mannyId, payload) {
            AudioManager.play(action === "transfer-deuterium-to-probe" ? "confirm" : "warning");
            if (window.backend) window.backend.runInventoryMannyAction(action, mannyId, payload);
        }

        function onLogbookCreateRequested(title, content) {
            AudioManager.play("save");
            if (window.backend) window.backend.createLogbookPage(title, content);
        }

        function onMessageSendRequested(payload) {
            AudioManager.play("confirm");
            if (window.backend) window.backend.sendMessage(payload);
        }

        function onMessageReadRequested(messageId) {
            AudioManager.play("select");
            if (window.backend) window.backend.markMessageRead(messageId);
        }

        function onLogbookUpdateRequested(pageId, title, content) {
            AudioManager.play("save");
            if (window.backend) window.backend.updateLogbookPage(pageId, title, content);
        }

        function onLogbookDeleteRequested(pageId) {
            AudioManager.play("warning");
            if (window.backend) window.backend.deleteLogbookPage(pageId);
        }

        function onAutoLogbookChanged(enabled) {
            AudioManager.play("press");
            if (window.backend) window.backend.setAutoLogbookEnabled(enabled);
        }

        function onLogbookPageOpenRequested(pageId) {
            AudioManager.play("select");
            if (window.backend) window.backend.loadLogbookPage(pageId);
        }

        function onOperatorManualRequested() {
            AudioManager.play("navigate");
            if (window.backend) window.backend.openOperatorManual();
        }

        function onChangeLogRequested() {
            AudioManager.play("navigate");
            if (window.backend) window.backend.openChangeLog();
        }

        function onUpdateCheckRequested() {
            AudioManager.play("navigate");
            if (window.backend) window.backend.checkForUpdates();
        }
    }

    Rectangle {
        anchors.fill: parent; z: 2000
        visible: window.backend && window.backend.shuttingDown
        color: Qt.rgba(0.01, 0.04, 0.06, 0.94)
        ColumnLayout {
            anchors.centerIn: parent; spacing: 12
            BusyIndicator { Layout.alignment: Qt.AlignHCenter; running: parent.parent.visible }
            Label { text: "SHUTTING DOWN SAFELY"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 24; font.bold: true }
            Label { text: "Waiting for active network and automation work to finish…"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
        }
    }
}
