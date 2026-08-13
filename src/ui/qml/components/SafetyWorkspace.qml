pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var alerts: []
    property var recovery: ({})
    signal mindSnapshotReassignRequested()

    ColumnLayout {
        anchors.fill: parent; spacing: 14
        GroupBox {
            visible: Boolean(root.recovery.available)
            title: "CRITICAL · TERMINAL PROBE RECOVERY"; Layout.fillWidth: true
            ColumnLayout {
                anchors.fill: parent; spacing: 10
                Label { Layout.fillWidth: true; text: String(root.recovery.probeName || "Default probe").toUpperCase() + " · " + String(root.recovery.status || "terminal").split("_").join(" ").toUpperCase(); color: Constants.criticalColor; font.bold: true; font.pixelSize: 18; wrapMode: Text.Wrap }
                Label { Layout.fillWidth: true; text: "The game permits reassignment of the last stable mind snapshot to a fresh probe chassis. This deletes the terminal probe state and resets the local coordinate reference frame so the new origin becomes FCC 0 / 0 / 0."; color: Constants.warningColor; wrapMode: Text.Wrap }
                Button { text: "REVIEW MIND-SNAPSHOT REASSIGNMENT"; onClicked: recoveryConfirmation.open() }
            }
        }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            ColumnLayout {
                width: parent.width; spacing: 10
                Repeater {
                    model: root.alerts
                    delegate: Rectangle {
                        id: alertCard; required property var modelData
                        Layout.fillWidth: true; implicitHeight: alertDetails.implicitHeight + 28
                        color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4
                        ColumnLayout { id: alertDetails; anchors.fill: parent; anchors.margins: 14
                            Label { Layout.fillWidth: true; text: alertCard.modelData.codeLabel || "SAFETY ALERT"; color: Constants.warningColor; font.bold: true; wrapMode: Text.Wrap }
                            Label { Layout.fillWidth: true; text: alertCard.modelData.summary || ""; color: Constants.mutedTextColor; wrapMode: Text.Wrap }
                        }
                    }
                }
                Label { visible: root.alerts.length === 0 && !root.recovery.available; Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; text: "No active safety findings."; color: Constants.nominalColor }
            }
        }
    }

    Dialog {
        id: recoveryConfirmation; anchors.centerIn: parent; modal: true
        title: "CONFIRM TERMINAL MIND-SNAPSHOT RECOVERY"; standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: root.mindSnapshotReassignRequested()
        Label { width: 620; text: "IRREVERSIBLE: the dead or black-hole-trapped default probe is deleted, a fresh chassis receives the last stable mind snapshot, and all relative coordinates are reset around a new FCC 0 / 0 / 0 origin."; color: Constants.criticalColor; font.bold: true; wrapMode: Text.Wrap }
    }
}
