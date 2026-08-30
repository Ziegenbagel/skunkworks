pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var alerts: []
    property var recovery: ({})
    property var pendingAlert: ({})
    property double currentEpochMs: Date.now()
    signal mindSnapshotReassignRequested()
    signal alertDeleteRequested(string alertId, string domain)
    signal galaxyMapRequested()

    function countdown(epochMs) {
        const seconds = Math.max(0, Math.floor((Number(epochMs || 0) - currentEpochMs) / 1000));
        const minutes = Math.floor(seconds / 60);
        return String(minutes).padStart(2, "0") + ":" + String(seconds % 60).padStart(2, "0");
    }

    Timer {
        interval: 1000
        running: root.visible && root.alerts.some(item => Boolean(item.remoteMannyLaserTargeted))
        repeat: true
        triggeredOnStart: true
        onTriggered: root.currentEpochMs = Date.now()
    }

    ListView {
        id: safetyAlertList
        anchors.fill: parent
        clip: true
        spacing: 14
        model: root.alerts
        cacheBuffer: 240
        headerPositioning: ListView.InlineHeader
        header: GroupBox {
            width: safetyAlertList.width
            visible: Boolean(root.recovery.available)
            height: visible ? implicitHeight : 0
            title: "CRITICAL · TERMINAL PROBE RECOVERY"
            ColumnLayout { anchors.fill: parent; spacing: 10
                Label { Layout.fillWidth: true; text: String(root.recovery.probeName || "Default probe").toUpperCase() + " · " + String(root.recovery.status || "terminal").split("_").join(" ").toUpperCase(); color: Constants.criticalColor; font.bold: true; font.pixelSize: 19; wrapMode: Text.WrapAtWordBoundaryOrAnywhere }
                Label { Layout.fillWidth: true; text: "The game permits reassignment of the last stable mind snapshot to a fresh probe chassis. This deletes the terminal probe state and resets the local coordinate reference frame so the new origin becomes FCC 0 / 0 / 0."; color: Constants.warningColor; font.pixelSize: 16; lineHeight: 1.25; wrapMode: Text.WrapAtWordBoundaryOrAnywhere }
                Button { text: "REVIEW MIND-SNAPSHOT REASSIGNMENT"; onClicked: recoveryConfirmation.open() }
            }
        }
        delegate: Rectangle {
                    id: alertCard; required property var modelData
                    width: safetyAlertList.width
                    height: Math.max(86, alertDetails.implicitHeight + 36)
                    color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4
                    ColumnLayout {
                        id: alertDetails
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 8
                        Label {
                            Layout.fillWidth: true
                            text: alertCard.modelData.codeLabel || "SAFETY ALERT"
                            color: Constants.warningColor
                            font.family: Constants.technicalFont
                            font.bold: true
                            font.pixelSize: 17
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                        Label {
                            visible: Boolean(alertCard.modelData.remoteMannyLaserTargeted)
                            Layout.fillWidth: true
                            text: "REMOTE MANNY LASER LOCK · DESTRUCTION "
                                  + root.countdown(alertCard.modelData.destructionEpochMs)
                                  + " · " + String(alertCard.modelData.sectorLabel || "SECTOR UNKNOWN")
                            color: Constants.criticalColor
                            font.family: Constants.technicalFont
                            font.bold: true
                            font.pixelSize: 18
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                        Label {
                            Layout.fillWidth: true
                            text: alertCard.modelData.summary || ""
                            color: Constants.mutedTextColor
                            font.family: Constants.bodyFont
                            font.pixelSize: 16
                            lineHeight: 1.3
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                        Image {
                            visible: String(alertCard.modelData.illustrationImageUrl || "").length > 0
                            Layout.fillWidth: true
                            Layout.preferredHeight: visible && implicitWidth > 0
                                ? Math.min(420, width * implicitHeight / implicitWidth) : 0
                            source: alertCard.modelData.illustrationImageUrl || ""
                            fillMode: Image.PreserveAspectFit
                            asynchronous: true
                        }
                        Button {
                            visible: Boolean(alertCard.modelData.remoteMannyLaserTargeted)
                            text: "SHOW SECTOR ON GALAXY MAP"
                            onClicked: root.galaxyMapRequested()
                        }
                        Button {
                            visible: Boolean(alertCard.modelData.deletable)
                            text: "DELETE ALERT"
                            Layout.alignment: Qt.AlignRight
                            onClicked: {
                                root.pendingAlert = alertCard.modelData;
                                deleteAlertConfirmation.open();
                            }
                        }
                    }
        }
        footer: Label {
            width: safetyAlertList.width
            height: visible ? implicitHeight + 20 : 0
            visible: root.alerts.length === 0 && !root.recovery.available
            horizontalAlignment: Text.AlignHCenter
            text: "No active safety findings."
            color: Constants.nominalColor; font.pixelSize: 16
        }
    }

    Dialog {
        id: recoveryConfirmation; anchors.centerIn: parent; modal: true
        title: "CONFIRM TERMINAL MIND-SNAPSHOT RECOVERY"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.mindSnapshotReassignRequested()
        Label { width: 620; text: "IRREVERSIBLE: the dead or black-hole-trapped default probe is deleted, a fresh chassis receives the last stable mind snapshot, and all relative coordinates are reset around a new FCC 0 / 0 / 0 origin."; color: Constants.criticalColor; font.bold: true; wrapMode: Text.Wrap }
    }
    Dialog {
        id: deleteAlertConfirmation; anchors.centerIn: parent; modal: true
        title: "DELETE ALERT"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.alertDeleteRequested(
            String(root.pendingAlert.id || ""),
            String(root.pendingAlert.domain || "alerts")
        )
        Label { width: 520; text: "Permanently delete this alert from the game and Skunkworks history? This cannot be undone."; color: Constants.warningColor; wrapMode: Text.Wrap }
    }
}
