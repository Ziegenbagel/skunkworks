import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"

Rectangle {
    id: root
    color: Constants.voidColor

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            color: Constants.panelColor
            border.color: Constants.lineColor

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                spacing: 18

                Label {
                    text: "SKUNKWORKS"
                    color: Constants.textColor
                    font.family: Constants.displayFont
                    font.pixelSize: 20
                    font.bold: true
                    font.letterSpacing: 2
                }

                Rectangle {
                    Layout.preferredWidth: 1
                    Layout.preferredHeight: 28
                    color: Constants.lineColor
                }

                Label {
                    text: "MISSION CONTROL"
                    color: Constants.cyanColor
                    font.family: Constants.technicalFont
                    font.pixelSize: 12
                    font.letterSpacing: 1.5
                }

                Item { Layout.fillWidth: true }

                ComboBox {
                    Layout.preferredWidth: 220
                    model: ["TEST PROBE · GENERIC"]
                }

                StatusPill {
                    label: "CONNECTED"
                }

                Button {
                    text: "OBSERVE"
                }

                Button {
                    text: "EMERGENCY STOP"
                    palette.buttonText: Constants.criticalColor
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.preferredWidth: 190
                Layout.fillHeight: true
                color: "#0b1219"
                border.color: Constants.lineColor

                Column {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 6

                    Repeater {
                        model: [
                            "OVERVIEW", "FLEET", "OPERATIONS", "NAVIGATION",
                            "INDUSTRY", "COMMUNICATIONS", "TIMELINE", "SETTINGS"
                        ]

                        delegate: Rectangle {
                            id: navigationItem
                            required property string modelData
                            width: parent.width
                            height: 42
                            radius: 2
                            color: modelData === "OVERVIEW"
                                ? Constants.selectedColor : "transparent"

                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 14
                                text: navigationItem.modelData
                                color: navigationItem.modelData === "OVERVIEW"
                                    ? Constants.cyanColor : Constants.mutedTextColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 11
                                font.bold: navigationItem.modelData === "OVERVIEW"
                            }
                        }
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                GridLayout {
                    width: Math.max(900, parent.width)
                    columns: 12
                    rowSpacing: 14
                    columnSpacing: 14
                    anchors.margins: 18

                    Label {
                        Layout.columnSpan: 12
                        Layout.fillWidth: true
                        text: "COMMAND OVERVIEW"
                        color: Constants.textColor
                        font.family: Constants.displayFont
                        font.pixelSize: 24
                        font.bold: true
                        font.letterSpacing: 1.5
                    }

                    Label {
                        Layout.columnSpan: 12
                        Layout.fillWidth: true
                        text: "Fleet posture, active operations, and constraints requiring attention"
                        color: Constants.mutedTextColor
                        font.pixelSize: 13
                    }

                    PanelFrame {
                        Layout.columnSpan: 8
                        Layout.fillWidth: true
                        Layout.preferredHeight: 250
                        title: "Fleet Readiness"

                        contentItem: Column {
                            spacing: 12
                            Label {
                                text: "85%"
                                color: Constants.nominalColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 46
                                font.bold: true
                            }
                            Label {
                                text: "1 probe idle · 1 Manny available · telemetry current"
                                color: Constants.textColor
                            }
                            ProgressBar {
                                width: 520
                                value: 0.85
                            }
                        }
                    }

                    PanelFrame {
                        Layout.columnSpan: 4
                        Layout.fillWidth: true
                        Layout.preferredHeight: 250
                        title: "Focused Probe"

                        contentItem: Column {
                            spacing: 10
                            Label { text: "TEST PROBE"; color: Constants.textColor; font.bold: true }
                            Label { text: "DEUTERIUM  50%"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                            Label { text: "CARGO FREE  5.0"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                            Label { text: "STATUS  IDLE"; color: Constants.nominalColor; font.family: Constants.technicalFont }
                        }
                    }

                    PanelFrame {
                        Layout.columnSpan: 7
                        Layout.fillWidth: true
                        Layout.preferredHeight: 280
                        title: "Active Operations"

                        contentItem: Column {
                            spacing: 12
                            Label { text: "No active operations"; color: Constants.textColor }
                            Label {
                                text: "Create an operation from a reviewed template."
                                color: Constants.mutedTextColor
                            }
                            Button { text: "NEW OPERATION" }
                        }
                    }

                    PanelFrame {
                        Layout.columnSpan: 5
                        Layout.fillWidth: true
                        Layout.preferredHeight: 280
                        title: "Attention"

                        contentItem: Column {
                            spacing: 12
                            StatusPill { label: "1 WARNING"; statusColor: Constants.warningColor }
                            Label {
                                width: parent.width
                                wrapMode: Text.WordWrap
                                text: "Inventory is approaching its configured reserve threshold."
                                color: Constants.textColor
                            }
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            color: Constants.panelColor
            border.color: Constants.lineColor

            Label {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 18
                text: "SNAPSHOT CURRENT  ·  API v104  ·  AUTOMATION OBSERVE-ONLY"
                color: Constants.mutedTextColor
                font.family: Constants.technicalFont
                font.pixelSize: 10
            }
        }
    }
}

/*##^##
Designer {
    D{i:0}D{i:10;locked:true}
}
##^##*/
