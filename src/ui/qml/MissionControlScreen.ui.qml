pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Rectangle {
    id: root
    objectName: "missionControlScreen"
    property bool liveMode: false
    property bool refreshing: false
    property string connectionError: ""
    property bool emergencyStopActive: false
    property var dashboardData: ({})
    readonly property var focusData: dashboardData.focus || ({})
    readonly property var fleetData: dashboardData.fleet || ({})
    readonly property var probeData: dashboardData.probe || ({})
    readonly property var healthData: dashboardData.health || ({})
    readonly property real focusedHullPercent: Number(probeData.integrityPercent === undefined ? 100 : probeData.integrityPercent)
    readonly property bool criticalHull: focusedHullPercent <= 10
    onCriticalHullChanged: if (criticalHull) AudioManager.play("warning")
    readonly property var resourceRows: dashboardData.resources && dashboardData.resources.length ? dashboardData.resources : liveMode ? [] : [
        {
            "name": "Deuterium",
            "amount": 482,
            "capacity": 1000,
            "label": "DEUTERIUM",
            "reading": "482 ECE",
            "value": 0.48
        },
        {
            "name": "Metals",
            "amount": 2814,
            "capacity": 4000,
            "label": "METALS",
            "reading": "2,814 ECE",
            "value": 0.72
        },
        {
            "name": "Carbon",
            "amount": 921,
            "capacity": 2500,
            "label": "CARBON",
            "reading": "921 ECE",
            "value": 0.36
        },
        {
            "name": "Ice",
            "amount": 1200,
            "capacity": 2000,
            "label": "ICE",
            "reading": "1,200 ECE",
            "value": 0.58
        }
    ]
    readonly property var previewProbes: [
        {
            "id": 1,
            "name": "Manny One",
            "model": "generic",
            "status": "idle",
            "sectorLabel": "FCC 0 / 0 / 0",
            "isReachable": true
        },
        {
            "id": 2,
            "name": "D-Tanker 01",
            "model": "deuterium_tanker",
            "status": "idle",
            "sectorLabel": "FCC 4 / -2 / 1",
            "isReachable": true
        }
    ]
    property var availableProbes: previewProbes
    property int focusedProbeId: availableProbes.length ? availableProbes[0].id : -1
    property string currentNavigation: "MISSION CONTROL"
    property alias probeSelectorControl: probeSelector
    property alias navigationBarControl: navigationBar
    property alias navigationWorkspaceControl: navigationWorkspace
    property alias emergencyStopControl: emergencyStopButton
    property alias alertsButtonControl: alertsButton
    readonly property real viewportScale: Math.min(width / Constants.width, height / Constants.height)
    readonly property real uiScale: 1.0
    readonly property int gutter: Math.round(12 * uiScale)
    width: Constants.width
    height: Constants.height
    implicitWidth: Constants.width
    implicitHeight: Constants.height
    color: Constants.voidColor

    Item {
        id: designCanvas
        anchors.centerIn: parent
        width: Constants.width
        height: Constants.height
        scale: root.viewportScale

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: root.gutter
            spacing: Math.round(10 * root.uiScale)

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(112 * root.uiScale)
                Layout.minimumHeight: Layout.preferredHeight
                Layout.maximumHeight: Layout.preferredHeight
                color: Constants.panelColor
                border.color: Constants.cyanColor
                radius: 3

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: Math.round(22 * root.uiScale)
                        Layout.rightMargin: Math.round(22 * root.uiScale)

                        Row {
                            spacing: 10
                            StatusPill {
                                label: "◉"
                                statusColor: root.connectionError || root.healthData.state === "critical" ? Constants.criticalColor : root.healthData.state === "degraded" ? Constants.warningColor : Constants.nominalColor
                            }
                            Column {
                                Label {
                                    text: "SYSTEM STATUS"
                                    color: Constants.mutedTextColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 8
                                }
                                Label {
                                    text: root.emergencyStopActive ? "AUTOMATION STOPPED" : root.healthData.stateLabel || (root.refreshing ? "REFRESHING" : "NOMINAL")
                                    color: root.emergencyStopActive || root.healthData.state === "critical" ? Constants.criticalColor : root.healthData.state === "degraded" ? Constants.warningColor : Constants.nominalColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            id: brandLine
                            Layout.preferredWidth: Math.round(620 * root.uiScale)
                            spacing: Math.round(18 * root.uiScale)
                            Label {
                                Layout.alignment: Qt.AlignLeft | Qt.AlignVCenter
                                text: "SKUNKWORKS"
                                color: Constants.textColor
                                font.family: Constants.displayFont
                                font.pixelSize: Math.round(30 * root.uiScale)
                                font.bold: true
                                font.letterSpacing: 2.8
                            }
                            Item { Layout.fillWidth: true }
                            Label {
                                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                                text: "AUTONOMOUS EXPLORATION & FLEET OPERATIONS"
                                color: Constants.cyanColor
                                font.family: Constants.technicalFont
                                font.pixelSize: Math.round(11 * root.uiScale)
                                font.bold: true
                                font.italic: true
                                font.letterSpacing: 1.1
                            }
                        }
                        Item {
                            Layout.fillWidth: true
                        }

                        ProbeSelector {
                            id: probeSelector
                            Layout.preferredWidth: 390
                            Layout.preferredHeight: 58
                            probeModel: root.availableProbes
                            currentProbeId: root.focusedProbeId
                            refreshing: root.refreshing
                        }

                        Item {
                            Layout.preferredWidth: 18
                        }

                        Row {
                            spacing: 10
                            Column {
                                Label {
                                    text: "NETWORK"
                                    color: Constants.mutedTextColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 8
                                }
                                Label {
                                    text: root.connectionError ? "ERROR  !" : root.refreshing ? "REFRESHING  …" : root.liveMode ? (root.dashboardData.connectionLabel || "CONNECTING") : "CONNECTED  ▮▮▮"
                                    color: root.connectionError ? Constants.criticalColor : root.dashboardData.connection === "stale" || root.dashboardData.connection === "limited_telemetry" ? Constants.warningColor : Constants.nominalColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }
                            Button {
                                id: emergencyStopButton
                                text: root.emergencyStopActive ? "▶ RESUME" : "■ STOP"
                                palette.buttonText: Constants.criticalColor
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Constants.lineColor
                    }

                    TopNavigationBar {
                        id: navigationBar
                        objectName: "topNavigationBar"
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(38 * root.uiScale)
                        Layout.leftMargin: Math.round(14 * root.uiScale)
                        Layout.rightMargin: Math.round(14 * root.uiScale)
                        currentSection: root.currentNavigation
                        newDailyReportCount: Number((root.dashboardData.logbook || {}).newDailyReportCount || 0)
                    }
                }
            }

            RowLayout {
                visible: root.currentNavigation === "MISSION CONTROL"
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: Math.round(10 * root.uiScale)

                ColumnLayout {
                    Layout.preferredWidth: Math.round(315 * root.uiScale)
                    Layout.minimumWidth: Layout.preferredWidth
                    Layout.maximumWidth: Layout.preferredWidth
                    Layout.fillHeight: true
                    spacing: Math.round(10 * root.uiScale)

                    PanelFrame {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(205 * root.uiScale)
                        Layout.minimumHeight: Layout.preferredHeight
                        Layout.maximumHeight: Layout.preferredHeight
                        title: "Fleet Status"
                        contentItem: Row {
                            anchors.centerIn: parent
                            spacing: 24
                            Rectangle {
                                width: 126
                                height: 126
                                radius: 63
                                color: Constants.voidColor
                                border.color: Constants.cyanColor
                                border.width: 8
                                Column {
                                    anchors.centerIn: parent
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: root.fleetData.total !== undefined ? root.fleetData.total : "14"
                                        color: Constants.textColor
                                        font.family: Constants.technicalFont
                                        font.pixelSize: 34
                                        font.bold: true
                                    }
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "TOTAL"
                                        color: Constants.mutedTextColor
                                        font.pixelSize: 11
                                    }
                                }
                            }
                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 13
                                Label {
                                    text: (root.fleetData.idle !== undefined ? root.fleetData.idle : "12") + "  OPERATIONAL"
                                    color: Constants.nominalColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                                Label {
                                    text: root.healthData.findings && root.healthData.findings.length ? (root.healthData.findings.length < 10 ? "0" : "") + root.healthData.findings.length + "  FINDINGS" : "00  FINDINGS"
                                    color: Constants.warningColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                                Label {
                                    text: (root.fleetData.total !== undefined ? root.fleetData.total - (root.fleetData.idle || 0) : "01") + "  ACTIVE"
                                    color: Constants.cyanColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                                Label {
                                    text: root.healthData.state === "critical" ? "01  CRITICAL" : "00  CRITICAL"
                                    color: Constants.criticalColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 14
                                    font.bold: true
                                }
                            }
                        }
                    }

                    PanelFrame {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(300 * root.uiScale)
                        Layout.minimumHeight: Layout.preferredHeight
                        Layout.maximumHeight: Layout.preferredHeight
                        title: "Resource Summary"
                        contentItem: Column {
                            width: parent.width
                            spacing: 6

                            Label {
                                width: parent.width
                                text: "STORAGE · " + Number((root.dashboardData.probe || {}).inventoryUsed || 0).toFixed(2)
                                      + " / " + Number((root.dashboardData.probe || {}).inventoryCapacity || 0).toFixed(2) + " ECE USED"
                                color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 11; font.bold: true
                            }

                            Repeater {
                                model: root.resourceRows
                                delegate: TelemetryBar {
                                    required property var modelData
                                    width: parent.width
                                    label: modelData.label
                                    value: modelData.value
                                    reading: modelData.reading
                                }
                            }
                        }
                    }

                    PanelFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: "Sector Resource Reserves"
                        contentItem: Column {
                            width: parent.width
                            spacing: 12
                            Repeater {
                                model: root.dashboardData.sectorResources || []
                                delegate: Row {
                                    required property var modelData
                                    width: parent.width; spacing: 8
                                    Label { width: parent.width * 0.62; text: modelData.label; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
                                    Label {
                                        text: Number(modelData.amount || 0).toFixed(Number(modelData.amount || 0) < 100 ? 2 : 0) + " ECE"
                                        color: Number(modelData.amount || 0) < 25 ? Constants.criticalColor : Number(modelData.amount || 0) < 100 ? Constants.warningColor : Constants.nominalColor
                                        font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true
                                    }
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumWidth: 0
                    spacing: Math.round(10 * root.uiScale)

                    PanelFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: "Live Sector · " + (root.dashboardData.sector ? root.dashboardData.sector.label : "FCC 0 / 0 / 0")
                        contentItem: SectorView {
                            anchors.fill: parent
                            previewMode: !root.liveMode
                            sectorData: root.dashboardData.sector || ({})
                            focusProbe: root.focusData
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(100 * root.uiScale)
                        Layout.minimumHeight: Layout.preferredHeight
                        Layout.maximumHeight: Layout.preferredHeight
                        color: "#150b0c"
                        border.color: Constants.criticalColor
                        radius: 3
                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 14
                            Image {
                                source: "../assets/icons/status-critical.png"
                                Layout.preferredWidth: 46
                                Layout.preferredHeight: 46
                                fillMode: Image.PreserveAspectFit
                            }
                            Repeater {
                                model: root.dashboardData.alerts && root.dashboardData.alerts.length ? root.dashboardData.alerts : [
                                    {
                                        "summary": "No active alerts",
                                        "severity": "nominal",
                                        "code": "SYSTEM",
                                        "codeLabel": "SYSTEM"
                                    }
                                ]
                                delegate: Rectangle {
                                    id: alertItem
                                    required property var modelData
                                    required property int index
                                    visible: alertItem.index < 3
                                    Layout.fillWidth: visible
                                    Layout.fillHeight: true
                                    color: alertItem.index % 2 ? "#1d1011" : "#150b0c"
                                    border.color: "#5b2529"
                                    border.width: 1
                                    Column {
                                        anchors.fill: parent; anchors.margins: 9; spacing: 3
                                        Label {
                                            width: parent.width
                                            text: (alertItem.index + 1) + " · " + alertItem.modelData.codeLabel
                                            color: Constants.textColor
                                            font.family: Constants.technicalFont
                                            font.pixelSize: 9
                                        }
                                        Label {
                                            width: parent.width
                                            text: alertItem.modelData.summary || "Unknown condition"
                                            color: alertItem.modelData.severity === "critical" ? Constants.criticalColor : alertItem.modelData.severity === "nominal" ? Constants.nominalColor : Constants.warningColor
                                            elide: Text.ElideRight
                                            font.bold: true
                                        }
                                    }
                                }
                            }
                            Item {
                                Layout.fillWidth: true
                            }
                            Button {
                                id: alertsButton
                                text: "VIEW ALERTS  ›"
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(190 * root.uiScale)
                        Layout.minimumHeight: Layout.preferredHeight
                        Layout.maximumHeight: Layout.preferredHeight
                        spacing: 10
                        PanelFrame {
                            objectName: "hullIntegrityPanel"
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.minimumWidth: 0
                            Layout.fillHeight: true
                            title: "Focused Probe Hull Integrity"
                            contentItem: Column {
                                width: parent.width; spacing: 10
                                Label {
                                    visible: root.criticalHull
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: "⚠ RED ALERT · CRITICAL HULL ⚠"
                                    color: Constants.criticalColor
                                    font.family: Constants.technicalFont; font.pixelSize: 14; font.bold: true
                                    SequentialAnimation on opacity {
                                        running: root.criticalHull; loops: Animation.Infinite
                                        NumberAnimation { to: 0.35; duration: 1300; easing.type: Easing.InOutSine }
                                        NumberAnimation { to: 1.0; duration: 1300; easing.type: Easing.InOutSine }
                                    }
                                }
                                Label {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: Number((root.dashboardData.probe || {}).integrityPercent === undefined ? 100 : root.dashboardData.probe.integrityPercent).toFixed(1) + "%"
                                    color: root.focusedHullPercent <= 10 ? Constants.criticalColor
                                          : root.focusedHullPercent <= 25 ? Constants.warningColor
                                          : Constants.nominalColor
                                    font.family: Constants.technicalFont; font.pixelSize: 28; font.bold: true
                                }
                                TelemetryBar {
                                    width: parent.width; label: "HULL"
                                    value: Number((root.dashboardData.probe || {}).integrityPercent || 0) / 100
                                    reading: Number((root.dashboardData.probe || {}).integrityPercent === undefined ? 100 : root.dashboardData.probe.integrityPercent).toFixed(1) + "%"
                                    showReading: false
                                    accentColor: root.focusedHullPercent <= 10 ? Constants.criticalColor
                                                 : root.focusedHullPercent <= 25 ? Constants.warningColor
                                                 : Constants.nominalColor
                                }
                            }
                        }
                        PanelFrame {
                            objectName: "safetyOverviewPanel"
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.minimumWidth: 0
                            Layout.fillHeight: true
                            title: "Safety Overview"
                            contentItem: Column {
                                width: parent.width; spacing: 10
                                Label {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: root.healthData.stateLabel || "SYSTEMS NOMINAL"
                                    color: root.healthData.state === "critical" ? Constants.criticalColor : root.healthData.state === "degraded" ? Constants.warningColor : Constants.nominalColor
                                    font.family: Constants.technicalFont; font.pixelSize: 18; font.bold: true
                                }
                                Label {
                                    width: parent.width; horizontalAlignment: Text.AlignHCenter
                                    text: root.healthData.summary || "No active threats detected"
                                    color: Constants.mutedTextColor; font.pixelSize: 15; wrapMode: Text.Wrap
                                }
                            }
                        }
                        SummaryListPanel {
                            objectName: "productionSummaryPanel"
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            Layout.minimumWidth: 0
                            Layout.fillHeight: true
                            title: "Production Queue"
                            detailTitle: "Production & Active Work · Full Details"
                            emptyText: "No active crafting, mining, or production work"
                            previewFontSize: 13
                            summaryFontSize: 11
                            entries: root.dashboardData.production || []
                        }
                    }
                }
            }

            NavigationWorkspace {
                id: navigationWorkspace
                objectName: "navigationWorkspace"
                visible: root.currentNavigation !== "MISSION CONTROL"
                Layout.fillWidth: true
                Layout.fillHeight: true
                section: root.currentNavigation
                dashboardData: root.dashboardData
                availableProbes: root.availableProbes
                focusedProbeId: root.focusedProbeId
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(26 * root.uiScale)
                Layout.minimumHeight: Layout.preferredHeight
                Layout.maximumHeight: Layout.preferredHeight
                Label {
                    text: "SKUNKWORKS MISSION CONTROL  ·  v"
                          + (root.dashboardData.appVersion || "DEVELOPMENT")
                    color: Constants.cyanColor
                    font.family: Constants.technicalFont
                    font.pixelSize: Math.round(12 * root.uiScale)
                    font.bold: true
                    font.letterSpacing: 1.6
                }
                Item {
                    Layout.fillWidth: true
                }
                Label {
                    text: "AUTONOMOUS FLEET OPERATIONS  ·  "
                          + (root.dashboardData.apiVersion
                             ? "GAME API v" + root.dashboardData.apiVersion
                             : "GAME API VERSION PENDING")
                          + "  ·  POLICY-CONTROLLED"
                    color: Constants.mutedTextColor
                    font.family: Constants.technicalFont
                    font.pixelSize: Math.round(12 * root.uiScale)
                }
            }
        }
    }
}
