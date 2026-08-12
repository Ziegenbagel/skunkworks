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
        TabBar {
            id: roleTabs; Layout.fillWidth: true
            TabButton { text: "OWNED PROBE ROLES" }
            TabButton { text: "FOCUSED ROLE · " + root.focusedRole.replace(/_/g, " ").toUpperCase() }
        }
        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: roleTabs.currentIndex

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width - 20; spacing: 10
                    Label { Layout.fillWidth: true; text: "Assign fleet roles here. Role-specific controls for the focused probe are kept in the adjacent tab."; color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                    Label { visible: !root.canManageRoles; Layout.fillWidth: true; text: "LOCKED · Focus the main/default probe to change owned probe roles."; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true; wrapMode: Text.Wrap }
                    Repeater {
                        model: root.availableProbes
                        delegate: Rectangle {
                            id: roleRow; required property var modelData
                            Layout.fillWidth: true; implicitHeight: 58
                            color: Constants.raisedColor; border.color: Constants.lineColor; radius: 3
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 10; spacing: 16
                                Label { Layout.preferredWidth: 300; text: roleRow.modelData.name; color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true }
                                Label { Layout.preferredWidth: 190; text: String(roleRow.modelData.model || "generic").replace(/_/g, " ").toUpperCase(); color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                                ComboBox {
                                    Layout.preferredWidth: 240; enabled: root.canManageRoles
                                    model: root.roleOptions
                                    currentIndex: Math.max(0, root.roleOptions.indexOf(root.roleFor(roleRow.modelData.id)))
                                    onActivated: root.roleAssignmentRequested(Number(roleRow.modelData.id), String(currentText))
                                }
                                Label { Layout.fillWidth: true; text: roleRow.modelData.sectorLabel || "SECTOR UNKNOWN"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                            }
                        }
                    }
                }
            }

            Item {
                NavigationControl {
                    anchors.fill: parent
                    visible: root.focusedRole === "transport" || root.focusedRole === "deuterium_tanker"
                    roleSettingsOnly: true
                    automationData: root.settingsData
                    focusedProbe: root.focusedProbeData
                    availableProbes: root.availableProbes
                    onTransportCycleRequested: plan => root.transportCycleRequested(plan)
                    onTransportCycleStartRequested: operationId => root.transportCycleStartRequested(operationId)
                    onTransportCyclePauseRequested: operationId => root.transportCyclePauseRequested(operationId)
                    onTransportCycleDeleteRequested: operationId => root.transportCycleDeleteRequested(operationId)
                }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 20; spacing: 14
                    visible: root.focusedRole === "deuterium_reserve"
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
                    Item { Layout.fillHeight: true }
                }
                Label {
                    anchors.centerIn: parent
                    visible: ["transport", "deuterium_tanker", "deuterium_reserve"].indexOf(root.focusedRole) < 0
                    text: "MORE COMING SOON\nNo probe-specific settings are available for this role yet."
                    horizontalAlignment: Text.AlignHCenter; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 16
                }
            }
        }
    }
}
