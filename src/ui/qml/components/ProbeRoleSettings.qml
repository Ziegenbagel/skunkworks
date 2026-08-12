pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var settingsData: ({})
    property var availableProbes: []
    property var focusedProbeData: ({})
    property int focusedProbeId: -1
    property int defaultProbeId: -1
    readonly property bool canManageRoles: defaultProbeId >= 0 && focusedProbeId === defaultProbeId
    readonly property var roleOptions: ["unassigned", "hub", "miner", "transport", "deuterium_tanker", "deuterium_reserve", "explorer", "builder_support"]
    readonly property string focusedRole: roleFor(focusedProbeId)
    readonly property var focusedSettings: (settingsData.probeRoleSettings || {})[String(focusedProbeId)] || ({})
    signal roleAssignmentRequested(int probeId, string role)
    signal roleSettingsSaveRequested(int probeId, var settings)
    signal transportCycleRequested(var plan)
    signal transportCycleStartRequested(string operationId)
    signal transportCyclePauseRequested(string operationId)
    signal transportCycleDeleteRequested(string operationId)

    function roleFor(probeId) {
        return String((settingsData.probeRoles || {})[String(probeId)] || "unassigned");
    }
    function probeName(probeId) {
        for (let i = 0; i < availableProbes.length; ++i)
            if (Number(availableProbes[i].id) === Number(probeId))
                return String(availableProbes[i].name || ("Probe " + probeId));
        return "Probe " + probeId;
    }
    function targetIndex() {
        const target = Number(focusedSettings.targetProbeId || -1);
        for (let i = 0; i < availableProbes.length; ++i)
            if (Number(availableProbes[i].id) === target) return i;
        return -1;
    }

    ColumnLayout {
        anchors.fill: parent; spacing: 12
        Label {
            Layout.fillWidth: true
            text: "PROBE ROLE SETTINGS · " + root.probeName(root.focusedProbeId).toUpperCase()
            color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true
        }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            ColumnLayout {
                width: Math.max(1, parent.width - 20); spacing: 14
                GroupBox {
                    visible: root.canManageRoles
                    title: "OWNED PROBE ROLES · DEFAULT PROBE CONTROL"
                    Layout.fillWidth: true
                    ColumnLayout {
                        anchors.fill: parent; spacing: 10
                        Label { Layout.fillWidth: true; text: "Assign one fleet role to each owned probe. These controls appear only while the default probe is focused."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                    Repeater {
                        model: root.availableProbes
                            delegate: Rectangle {
                            id: roleRow; required property var modelData
                                Layout.fillWidth: true; implicitHeight: 62
                            color: Constants.raisedColor; border.color: Constants.lineColor; radius: 3
                            RowLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 20
                                    Label { Layout.preferredWidth: 320; Layout.maximumWidth: 320; elide: Text.ElideRight; text: roleRow.modelData.name; color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true }
                                    Label { Layout.preferredWidth: 210; Layout.maximumWidth: 210; text: String(roleRow.modelData.model || "generic").replace(/_/g, " ").toUpperCase(); color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                                ComboBox {
                                        Layout.preferredWidth: 270
                                    model: root.roleOptions
                                    currentIndex: Math.max(0, root.roleOptions.indexOf(root.roleFor(roleRow.modelData.id)))
                                    onActivated: root.roleAssignmentRequested(Number(roleRow.modelData.id), String(currentText))
                                }
                                    Label { Layout.fillWidth: true; elide: Text.ElideRight; text: roleRow.modelData.sectorLabel || "SECTOR UNKNOWN"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                            }
                        }
                    }
                }
            }
                Label {
                    Layout.fillWidth: true
                    text: "FOCUSED ROLE · " + root.focusedRole.replace(/_/g, " ").toUpperCase()
                    color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true
                }
                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 730
                    visible: root.focusedRole === "transport" || root.focusedRole === "deuterium_tanker"
                NavigationControl {
                    anchors.fill: parent
                    roleSettingsOnly: true
                    automationData: root.settingsData
                    focusedProbe: root.focusedProbeData
                    availableProbes: root.availableProbes
                    onTransportCycleRequested: plan => root.transportCycleRequested(plan)
                    onTransportCycleStartRequested: operationId => root.transportCycleStartRequested(operationId)
                    onTransportCyclePauseRequested: operationId => root.transportCyclePauseRequested(operationId)
                    onTransportCycleDeleteRequested: operationId => root.transportCycleDeleteRequested(operationId)
                }
                }
                GroupBox {
                    visible: root.focusedRole === "deuterium_reserve"
                    title: "RESERVE TANKER REFILL CHAIN"
                    Layout.fillWidth: true
                    ColumnLayout {
                    anchors.fill: parent; spacing: 14
                    Label { text: "RESERVE TANKER REFILL CHAIN"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 17; font.bold: true }
                    Label { Layout.fillWidth: true; text: "This tanker checks only the selected probe. Multiple reserve tankers can be chained by selecting the next tanker or final consumer for each link."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                    GridLayout {
                        columns: 2; columnSpacing: 18; rowSpacing: 12
                        Label { text: "MONITOR & REFILL PROBE"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                        ComboBox { id: reserveTarget; Layout.preferredWidth: 420; textRole: "name"; valueRole: "id"; model: root.availableProbes; currentIndex: root.targetIndex() }
                        Label { text: "PROTECTED SOURCE RESERVE"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                        RowLayout { SpinBox { id: protectedReserve; from: 0; to: 800; editable: true; value: Number(root.focusedSettings.protectedDeuterium || root.focusedSettings.reserve || 0) } Label { text: "ECE" } }
                    }
                    Button {
                        text: "SAVE RESERVE ROLE SETTINGS"
                        enabled: reserveTarget.currentIndex >= 0 && Number(reserveTarget.currentValue) !== root.focusedProbeId
                        onClicked: root.roleSettingsSaveRequested(root.focusedProbeId, {"targetProbeId": Number(reserveTarget.currentValue), "protectedDeuterium": Number(protectedReserve.value)})
                    }
                    Label { visible: reserveTarget.currentIndex >= 0 && Number(reserveTarget.currentValue) === root.focusedProbeId; text: "A reserve tanker cannot refill itself."; color: Constants.criticalColor; font.family: Constants.technicalFont }
                    }
                }
                Label {
                    Layout.fillWidth: true; Layout.topMargin: 80
                    visible: ["transport", "deuterium_tanker", "deuterium_reserve"].indexOf(root.focusedRole) < 0
                    text: "MORE COMING SOON\nNo probe-specific settings are available for this role yet."
                    horizontalAlignment: Text.AlignHCenter; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 16
                }
            }
        }
    }
}
