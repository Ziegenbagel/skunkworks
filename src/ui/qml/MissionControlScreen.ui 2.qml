import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Rectangle {
    id: root
    property bool liveMode: false
    property bool refreshing: false
    property string connectionError: ""
    property var dashboardData: ({})
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
    property alias probeSelectorControl: probeSelector
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
                                statusColor: Constants.nominalColor
                            }
                            Column {
                                Label {
                                    text: "SYSTEM STATUS"
                                    color: Constants.mutedTextColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 8
                                }
                                Label {
                                    text: "NOMINAL"
                                    color: Constants.nominalColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                        Column {
                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "SKUNKWORKS"
                                color: Constants.textColor
                                font.family: Constants.displayFont
                                font.pixelSize: Math.round(25 * root.uiScale)
                                font.bold: true
                                font.letterSpacing: 2.4
                            }
                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "AUTONOMOUS EXPLORATION & FLEET OPERATIONS"
                                color: Constants.cyanColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 8
                                font.letterSpacing: 1.5
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
                                    text: "CONNECTED  ▮▮▮"
                                    color: Constants.nominalColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                            }
                            Button {
                                text: "■ STOP"
                                palette.buttonText: Constants.criticalColor
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Constants.lineColor
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(38 * root.uiScale)
                        Layout.leftMargin: Math.round(14 * root.uiScale)
                        Layout.rightMargin: Math.round(14 * root.uiScale)
                        spacing: 3

                        Repeater {
                            model: ["MISSION CONTROL", "FLEET", "GALAXY MAP", "RESOURCES", "MISSIONS", "PRODUCTION", "RESEARCH", "SAFETY", "LOGBOOK", "SETTINGS"]
                            delegate: Rectangle {
                                id: topNavigation
                                required property string modelData
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                color: topNavigation.modelData === "MISSION CONTROL" ? Constants.selectedColor : "transparent"
                                border.color: topNavigation.modelData === "MISSION CONTROL" ? Constants.cyanColor : "transparent"
                                Label {
                                    anchors.centerIn: parent
                                    width: parent.width - 4
                                    text: topNavigation.modelData
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                    color: topNavigation.modelData === "MISSION CONTROL" ? Constants.cyanColor : Constants.mutedTextColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 8
                                    font.bold: topNavigation.modelData === "MISSION CONTROL"
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
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
                            spacing: 18
                            Rectangle {
                                width: 92
                                height: 92
                                radius: 46
                                color: Constants.voidColor
                                border.color: Constants.cyanColor
                                border.width: 8
                                Column {
                                    anchors.centerIn: parent
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "14"
                                        color: Constants.textColor
                                        font.family: Constants.technicalFont
                                        font.pixelSize: 26
                                    }
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: "TOTAL"
                                        color: Constants.mutedTextColor
                                        font.pixelSize: 8
                                    }
                                }
                            }
                            Column {
                                spacing: 9
                                Label {
                                    text: "12  OPERATIONAL"
                                    color: Constants.nominalColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 10
                                }
                                Label {
                                    text: "01  LOW FUEL"
                                    color: Constants.warningColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 10
                                }
                                Label {
                                    text: "01  IN REPAIR"
                                    color: Constants.cyanColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 10
                                }
                                Label {
                                    text: "00  CRITICAL"
                                    color: Constants.criticalColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }

                    PanelFrame {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(258 * root.uiScale)
                        Layout.minimumHeight: Layout.preferredHeight
                        Layout.maximumHeight: Layout.preferredHeight
                        title: "Resource Summary"
                        contentItem: Column {
                            width: parent.width
                            spacing: 8
                            TelemetryBar {
                                width: parent.width
                                label: "DEUTERIUM"
                                value: 0.48
                                reading: "482 ECE"
                            }
                            TelemetryBar {
                                width: parent.width
                                label: "METALS"
                                value: 0.72
                                reading: "2,814 ECE"
                            }
                            TelemetryBar {
                                width: parent.width
                                label: "CARBON"
                                value: 0.36
                                reading: "921 ECE"
                            }
                            TelemetryBar {
                                width: parent.width
                                label: "ICE"
                                value: 0.58
                                reading: "1,200 ECE"
                            }
                        }
                    }

                    PanelFrame {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        title: "Safety Overview"
                        contentItem: Column {
                            width: parent.width
                            spacing: 14
                            Image {
                                width: 60
                                height: 60
                                anchors.horizontalCenter: parent.horizontalCenter
                                source: "../assets/icons/status-shield.png"
                                fillMode: Image.PreserveAspectFit
                            }
                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "SYSTEMS NOMINAL"
                                color: Constants.nominalColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 11
                                font.bold: true
                            }
                            Label {
                                anchors.horizontalCenter: parent.horizontalCenter
                                text: "No active threats detected"
                                color: Constants.mutedTextColor
                                font.pixelSize: 10
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
                        title: "Live Sector · FCC 0 / 0 / 0"
                        contentItem: SectorView {
                            anchors.fill: parent
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
                            Column {
                                Label {
                                    text: "PROBE EXPLORER-07"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                                Label {
                                    text: "LOW FUEL"
                                    color: Constants.warningColor
                                    font.bold: true
                                }
                            }
                            Rectangle {
                                Layout.preferredWidth: 1
                                Layout.fillHeight: true
                                color: "#682326"
                            }
                            Column {
                                Label {
                                    text: "DEUTERIUM SOURCE"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                                Label {
                                    text: "DEPLETING · 12h 34m"
                                    color: Constants.warningColor
                                    font.bold: true
                                }
                            }
                            Rectangle {
                                Layout.preferredWidth: 1
                                Layout.fillHeight: true
                                color: "#682326"
                            }
                            Column {
                                Label {
                                    text: "PRODUCTION QUEUE"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                                Label {
                                    text: "BACKLOG · 2 DELAYED"
                                    color: Constants.warningColor
                                    font.bold: true
                                }
                            }
                            Item {
                                Layout.fillWidth: true
                            }
                            Button {
                                text: "VIEW ALERTS  ›"
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.round(155 * root.uiScale)
                        Layout.minimumHeight: Layout.preferredHeight
                        Layout.maximumHeight: Layout.preferredHeight
                        spacing: 10
                        PanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Active Missions"
                            contentItem: Column {
                                width: parent.width
                                spacing: 10
                                Label {
                                    text: "✧  Explorer-01    Journey to SCUT Origin       42%"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                                Label {
                                    text: "◇  Builder-02     Establish Forward Hub       68%"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                                Label {
                                    text: "◆  Miner-03       Deuterium Acquisition       25%"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                            }
                        }
                        PanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Production Queue"
                            contentItem: Column {
                                width: parent.width
                                spacing: 10
                                Label {
                                    text: "MANNY                  02h 14m        76%"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                                Label {
                                    text: "STORAGE CONTAINER      01h 03m        54%"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                                Label {
                                    text: "PROBE                  05h 47m        31%"
                                    color: Constants.textColor
                                    font.family: Constants.technicalFont
                                    font.pixelSize: 9
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.round(22 * root.uiScale)
                Layout.minimumHeight: Layout.preferredHeight
                Layout.maximumHeight: Layout.preferredHeight
                Label {
                    text: "SKUNKWORKS UI CONCEPT v1.0"
                    color: Constants.cyanColor
                    font.family: Constants.technicalFont
                    font.pixelSize: 9
                    font.letterSpacing: 2
                }
                Item {
                    Layout.fillWidth: true
                }
                Label {
                    text: "AEROSPACE OPERATIONS CONSOLE  ·  API v" + (root.dashboardData.apiVersion || "103–107") + "  ·  POLICY-CONTROLLED"
                    color: Constants.mutedTextColor
                    font.family: Constants.technicalFont
                    font.pixelSize: 9
                }
            }
        }
    }
}
