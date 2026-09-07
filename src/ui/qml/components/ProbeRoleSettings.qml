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
    property var runtimeData: ({})
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
            id: roleScroll
            objectName: "probeRoleSettingsScroll"
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            contentWidth: availableWidth
            contentHeight: roleSettingsContent.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn
            ColumnLayout {
                id: roleSettingsContent
                width: Math.max(1, roleScroll.availableWidth); spacing: 14
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
                    Layout.minimumWidth: roleScroll.availableWidth
                    // Expand the embedded form to its complete laid-out height. The
                    // enclosing roleScroll is the only vertical scroller on this page.
                    Layout.preferredHeight: Math.max(
                        730,
                        Math.ceil(transportRoleControl.transportContentExtent)
                            + 24
                    )
                    Layout.minimumHeight: Layout.preferredHeight
                    visible: root.focusedRole === "transport" || root.focusedRole === "deuterium_tanker"
                NavigationControl {
                    id: transportRoleControl
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
                        Label { text: "MONITOR AND REFILL PROBE"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
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
                GroupBox {
                    visible: root.focusedRole === "explorer"
                    title: "AUTONOMOUS FRONTIER EXPLORATION"
                    Layout.fillWidth: true
                    ColumnLayout {
                        anchors.fill: parent; spacing: 14
                        Label {
                            Layout.fillWidth: true
                            text: "The Explorer scans on arrival, remains inside verified SCUT coverage, and uses an idle Manny to inspect dormant constructs or derelict Others ships. Habitable-species contact always pauses until you review and acknowledge its alert in Safety."
                            color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap
                        }
                        Rectangle {
                            Layout.fillWidth: true; implicitHeight: explorerStatus.implicitHeight + 24
                            color: Constants.raisedColor; border.color: Constants.lineColor; radius: 3
                            Label {
                                id: explorerStatus
                                anchors.fill: parent; anchors.margins: 12
                                text: "STATUS · " + String((root.runtimeData.explorer || {}).phase || "NOT EVALUATED").replace(/_/g, " ").toUpperCase()
                                      + "\n" + String((root.runtimeData.explorer || {}).summary || "Save settings, then run or enable an automation cycle to evaluate the campaign.")
                                color: Boolean((root.runtimeData.explorer || {}).paused) ? Constants.warningColor : Constants.cyanColor
                                font.family: Constants.technicalFont; wrapMode: Text.Wrap
                            }
                        }
                        CheckBox {
                            id: explorerEnabled
                            text: "ENABLE AUTONOMOUS EXPLORATION"
                            checked: Boolean(root.focusedSettings.explorationEnabled)
                        }
                        RowLayout {
                            Label { text: "FRONTIER FOCUS"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                            ComboBox {
                                id: explorerMode
                                Layout.preferredWidth: 360
                                model: ["PLANETARY FRONTIER (WITH FALLBACK)", "ANY FRONTIER"]
                                currentIndex: String(root.focusedSettings.frontierMode || "planetary_frontier") === "any_frontier" ? 1 : 0
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: "Planetary focus prefers scans suggesting planets, then automatically falls back to the nearest ordinary unexplored sector instead of stalling. Existing global fuel, Metals, repair, and safe-hop settings remain authoritative."
                            color: Constants.mutedTextColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap
                        }
                        Button {
                            text: "SAVE EXPLORER ROLE SETTINGS"
                            onClicked: root.roleSettingsSaveRequested(root.focusedProbeId, {
                                "explorationEnabled": Boolean(explorerEnabled.checked),
                                "frontierMode": explorerMode.currentIndex === 1 ? "any_frontier" : "planetary_frontier"
                            })
                        }
                    }
                }
                Item {
                    visible: ["transport", "deuterium_tanker", "deuterium_reserve", "explorer"].indexOf(root.focusedRole) < 0
                    Layout.fillWidth: true
                    Layout.minimumWidth: roleScroll.availableWidth
                    Layout.preferredHeight: Math.max(300, roleScroll.availableHeight - 90)
                    Label {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 80, 760)
                    text: "MORE COMING SOON\nNo probe-specific settings are available for this role yet."
                    horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
                    color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 16
                    }
                }
            }
        }
    }
}
