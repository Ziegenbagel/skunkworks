pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Rectangle {
    id: root
    property bool credentialConfigured: false
    property string credentialMessage: ""
    property int page: 0
    signal apiKeySaveRequested(string apiKey)
    signal apiKeyTestRequested()
    signal finishRequested()

    onVisibleChanged: if (visible) page = 0

    color: Qt.rgba(0.01, 0.025, 0.04, 0.97)
    border.color: Constants.cyanColor

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 80, 1040)
        height: Math.min(parent.height - 80, 680)
        color: Constants.panelColor
        border.color: Constants.cyanColor
        radius: 4

        ColumnLayout {
            anchors.fill: parent; anchors.margins: 28; spacing: 16
            Label { text: "SKUNKWORKS · FIRST-LAUNCH SETUP"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 24; font.bold: true; font.letterSpacing: 2 }
            Label { text: "STEP " + (root.page + 1) + " OF 6"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
            ProgressBar { Layout.fillWidth: true; from: 0; to: 6; value: root.page + 1 }

            StackLayout {
                currentIndex: root.page; Layout.fillWidth: true; Layout.fillHeight: true
                ColumnLayout {
                    Label { text: "WELCOME, COMMANDER"; color: Constants.textColor; font.pixelSize: 24; font.bold: true }
                    Label { Layout.fillWidth: true; text: "This walkthrough connects your account and explains the controls that can affect probes. Skunkworks begins conservatively: information is live, while automation remains bounded by its execution mode, safety review, and emergency stop."; color: Constants.textColor; font.pixelSize: 15; wrapMode: Text.Wrap }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    Label { text: "CONNECT THE VON NEUMANN API"; color: Constants.textColor; font.pixelSize: 22; font.bold: true }
                    Label { Layout.fillWidth: true; text: "Paste the API key issued by the game. It will be stored in macOS Keychain, Windows Credential Manager, or the configured Linux secret-service backend—not in project files."; color: Constants.textColor; wrapMode: Text.Wrap }
                    TextField { id: wizardApiKey; Layout.fillWidth: true; echoMode: TextInput.Password; placeholderText: root.credentialConfigured ? "API key already configured" : "Paste API key" }
                    RowLayout {
                        Button { text: "SAVE SECURELY"; enabled: wizardApiKey.text.length > 0; onClicked: { root.apiKeySaveRequested(wizardApiKey.text); wizardApiKey.clear(); } }
                        Button { text: "TEST CONNECTION"; enabled: root.credentialConfigured; onClicked: root.apiKeyTestRequested() }
                        Label { text: root.credentialConfigured ? "✓ CREDENTIAL CONFIGURED" : "API KEY REQUIRED"; color: root.credentialConfigured ? Constants.nominalColor : Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                    }
                    Label { Layout.fillWidth: true; text: root.credentialMessage; color: Constants.cyanColor; wrapMode: Text.Wrap }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    Label { text: "PROBES, ROLES, AND FOCUS"; color: Constants.textColor; font.pixelSize: 22; font.bold: true }
                    Label { Layout.fillWidth: true; text: "The focused-probe selector changes every live dashboard domain, including sector, resources, Mannys, travel, and production. In Settings, assign each probe a role such as hub, miner, transport, tanker, reserve, explorer, or builder support."; color: Constants.textColor; wrapMode: Text.Wrap }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    Label { text: "TRAVEL, SCANS, AND MAPS"; color: Constants.textColor; font.pixelSize: 22; font.bold: true }
                    Label { Layout.fillWidth: true; text: "Navigation provides manual route previews, autonomous destinations, nearby passive scans, and live SCUT coverage. Manual movement always requires confirmation. The Galaxy tab is a rotatable X/Y/Z scene and preserves successful sector scans locally."; color: Constants.textColor; wrapMode: Text.Wrap }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    Label { text: "SAFETY AND AUTOMATION"; color: Constants.textColor; font.pixelSize: 22; font.bold: true }
                    Label { Layout.fillWidth: true; text: "Priorities use a simple 1–10 scale, with 1 highest; equal numbers receive equal priority. Desired quantities tell the planner what to maintain. Travel distance, integrity, fuel floors, forgotten Mannys, container detachment, resource depletion, and SCUT coverage remain subject to warnings and player acknowledgement. STOP immediately blocks automation."; color: Constants.textColor; wrapMode: Text.Wrap }
                    Item { Layout.fillHeight: true }
                }
                ColumnLayout {
                    Label { text: "READY FOR MISSION CONTROL"; color: Constants.nominalColor; font.pixelSize: 24; font.bold: true }
                    Label { Layout.fillWidth: true; text: "Setup can be reopened from Settings at any time. Finishing will connect to the live account and load the remembered probe."; color: Constants.textColor; wrapMode: Text.Wrap }
                    Label { text: root.credentialConfigured ? "✓ API CREDENTIAL READY" : "API KEY MUST BE CONFIGURED BEFORE FINISHING"; color: root.credentialConfigured ? Constants.nominalColor : Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                    Item { Layout.fillHeight: true }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Button { text: "BACK"; enabled: root.page > 0; onClicked: root.page-- }
                Item { Layout.fillWidth: true }
                Button { visible: root.page < 5; text: "NEXT"; enabled: root.page !== 1 || root.credentialConfigured; onClicked: root.page++ }
                Button { visible: root.page === 5; text: "FINISH & CONNECT"; enabled: root.credentialConfigured; onClicked: root.finishRequested() }
            }
        }
    }
}
