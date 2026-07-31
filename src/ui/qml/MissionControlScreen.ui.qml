import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Rectangle {
    id: root
    width: Constants.width
    height: Constants.height
    implicitWidth: Constants.width
    implicitHeight: Constants.height
    color: Constants.voidColor

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 112
            color: Constants.panelColor
            border.color: Constants.cyanColor
            radius: 3

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.leftMargin: 22
                    Layout.rightMargin: 22

                    Row {
                        spacing: 10
                        StatusPill { label: "◉"; statusColor: Constants.nominalColor }
                        Column {
                            Label { text: "SYSTEM STATUS"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
                            Label { text: "NOMINAL"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.pixelSize: 11; font.bold: true }
                        }
                    }

                    Item { Layout.fillWidth: true }
                    Column {
                        Label {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: "SKUNKWORKS"
                            color: Constants.textColor
                            font.family: Constants.displayFont
                            font.pixelSize: 25
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
                    Item { Layout.fillWidth: true }

                    Row {
                        spacing: 10
                        Column {
                            Label { text: "NETWORK"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
                            Label { text: "CONNECTED  ▮▮▮"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.pixelSize: 11; font.bold: true }
                        }
                        Button { text: "■ STOP"; palette.buttonText: Constants.criticalColor }
                    }
                }

                Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Constants.lineColor }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 38
                    Layout.leftMargin: 14
                    Layout.rightMargin: 14
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
                                text: topNavigation.modelData
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
            spacing: 10

            ColumnLayout {
                Layout.preferredWidth: 275
                Layout.fillHeight: true
                spacing: 10

                PanelFrame {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 205
                    title: "Fleet Status"
                    contentItem: Row {
                        spacing: 18
                        Rectangle {
                            width: 92; height: 92; radius: 46
                            color: Constants.voidColor
                            border.color: Constants.cyanColor; border.width: 8
                            Column {
                                anchors.centerIn: parent
                                Label { anchors.horizontalCenter: parent.horizontalCenter; text: "14"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 26 }
                                Label { anchors.horizontalCenter: parent.horizontalCenter; text: "TOTAL"; color: Constants.mutedTextColor; font.pixelSize: 8 }
                            }
                        }
                        Column {
                            spacing: 9
                            Label { text: "12  OPERATIONAL"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
                            Label { text: "01  LOW FUEL"; color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
                            Label { text: "01  IN REPAIR"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
                            Label { text: "00  CRITICAL"; color: Constants.criticalColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
                        }
                    }
                }

                PanelFrame {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 258
                    title: "Resource Summary"
                    contentItem: Column {
                        width: parent.width
                        spacing: 8
                        TelemetryBar { width: parent.width; label: "DEUTERIUM"; value: 0.48; reading: "482 ECE" }
                        TelemetryBar { width: parent.width; label: "METALS"; value: 0.72; reading: "2,814 ECE" }
                        TelemetryBar { width: parent.width; label: "CARBON"; value: 0.36; reading: "921 ECE" }
                        TelemetryBar { width: parent.width; label: "ICE"; value: 0.58; reading: "1,200 ECE" }
                    }
                }

                PanelFrame {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "Safety Overview"
                    contentItem: Column {
                        width: parent.width
                        spacing: 14
                        Image { width: 60; height: 60; anchors.horizontalCenter: parent.horizontalCenter; source: "../../assets/icons/status-shield.png"; fillMode: Image.PreserveAspectFit }
                        Label { anchors.horizontalCenter: parent.horizontalCenter; text: "SYSTEMS NOMINAL"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.pixelSize: 11; font.bold: true }
                        Label { anchors.horizontalCenter: parent.horizontalCenter; text: "No active threats detected"; color: Constants.mutedTextColor; font.pixelSize: 10 }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 10

                PanelFrame {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    title: "Live Sector · FCC 0 / 0 / 0"
                    contentItem: SectorView { anchors.fill: parent }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 100
                    color: "#150b0c"
                    border.color: Constants.criticalColor
                    radius: 3
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        Image { source: "../../assets/icons/status-critical.png"; Layout.preferredWidth: 46; Layout.preferredHeight: 46; fillMode: Image.PreserveAspectFit }
                        Column {
                            Label { text: "PROBE EXPLORER-07"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                            Label { text: "LOW FUEL"; color: Constants.warningColor; font.bold: true }
                        }
                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#682326" }
                        Column {
                            Label { text: "DEUTERIUM SOURCE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                            Label { text: "DEPLETING · 12h 34m"; color: Constants.warningColor; font.bold: true }
                        }
                        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: "#682326" }
                        Column {
                            Label { text: "PRODUCTION QUEUE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                            Label { text: "BACKLOG · 2 DELAYED"; color: Constants.warningColor; font.bold: true }
                        }
                        Item { Layout.fillWidth: true }
                        Button { text: "VIEW ALERTS  ›" }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 155
                    spacing: 10
                    PanelFrame {
                        Layout.fillWidth: true; Layout.fillHeight: true; title: "Active Missions"
                        contentItem: Column {
                            width: parent.width; spacing: 10
                            Label { text: "✧  Explorer-01    Journey to SCUT Origin       42%"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                            Label { text: "◇  Builder-02     Establish Forward Hub       68%"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                            Label { text: "◆  Miner-03       Deuterium Acquisition       25%"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                        }
                    }
                    PanelFrame {
                        Layout.fillWidth: true; Layout.fillHeight: true; title: "Production Queue"
                        contentItem: Column {
                            width: parent.width; spacing: 10
                            Label { text: "MANNY                  02h 14m        76%"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                            Label { text: "STORAGE CONTAINER      01h 03m        54%"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                            Label { text: "PROBE                  05h 47m        31%"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            Label { text: "SKUNKWORKS UI CONCEPT v1.0"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 9; font.letterSpacing: 2 }
            Item { Layout.fillWidth: true }
            Label { text: "AEROSPACE OPERATIONS CONSOLE  ·  API v104  ·  OBSERVE-ONLY"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
        }
    }
}
