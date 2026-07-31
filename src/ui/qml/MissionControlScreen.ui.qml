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
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 68
            color: Constants.panelColor
            border.color: Constants.lineColor

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22
                anchors.rightMargin: 22
                spacing: 16

                Column {
                    Layout.preferredWidth: 245
                    spacing: 1
                    Label {
                        text: "SKUNKWORKS"
                        color: Constants.textColor
                        font.family: Constants.displayFont
                        font.pixelSize: 20
                        font.bold: true
                        font.letterSpacing: 2.2
                    }
                    Label {
                        text: "VON NEUMANN OPERATIONS"
                        color: Constants.cyanColor
                        font.family: Constants.technicalFont
                        font.pixelSize: 8
                        font.letterSpacing: 2
                    }
                }

                Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 34; color: Constants.lineColor }
                Label {
                    text: "COMMAND OVERVIEW"
                    color: Constants.mutedTextColor
                    font.family: Constants.technicalFont
                    font.pixelSize: 11
                    font.letterSpacing: 1.4
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: "FOCUSED PROBE"
                    color: Constants.mutedTextColor
                    font.family: Constants.technicalFont
                    font.pixelSize: 8
                }
                ComboBox { Layout.preferredWidth: 210; model: ["MANNY ONE · GENERIC"] }
                StatusPill { label: "CONNECTED" }
                Button { text: "OBSERVE" }
                Button { text: "■  EMERGENCY STOP"; palette.buttonText: Constants.criticalColor }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.preferredWidth: 202
                Layout.fillHeight: true
                color: "#0b1219"
                border.color: Constants.lineColor

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 6

                    Repeater {
                        model: ["OVERVIEW", "FLEET", "OPERATIONS", "NAVIGATION", "INDUSTRY", "COMMS", "TIMELINE", "SETTINGS"]
                        delegate: Rectangle {
                            id: navigationItem
                            required property string modelData
                            Layout.fillWidth: true
                            Layout.preferredHeight: 43
                            radius: 2
                            color: navigationItem.modelData === "OVERVIEW" ? Constants.selectedColor : "transparent"
                            Rectangle {
                                visible: navigationItem.modelData === "OVERVIEW"
                                width: 3
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                color: Constants.cyanColor
                            }
                            Label {
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.left: parent.left
                                anchors.leftMargin: 16
                                text: navigationItem.modelData
                                color: navigationItem.modelData === "OVERVIEW" ? Constants.cyanColor : Constants.mutedTextColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 10
                                font.bold: navigationItem.modelData === "OVERVIEW"
                                font.letterSpacing: 0.8
                            }
                        }
                    }

                    Item { Layout.fillHeight: true }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Constants.lineColor }
                    Label {
                        text: "API 104\nSYNC  00:14 AGO\nPOLICY  BALANCED"
                        color: Constants.mutedTextColor
                        font.family: Constants.technicalFont
                        font.pixelSize: 9
                        lineHeight: 1.5
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                ColumnLayout {
                    width: Math.max(980, parent.width)
                    spacing: 14

                    Item { Layout.preferredHeight: 4 }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        Column {
                            Layout.fillWidth: true
                            Label {
                                text: "GOOD MORNING, COMMANDER"
                                color: Constants.textColor
                                font.family: Constants.displayFont
                                font.pixelSize: 23
                                font.bold: true
                                font.letterSpacing: 1.2
                            }
                            Label {
                                text: "Fleet posture is stable. One condition requires review."
                                color: Constants.mutedTextColor
                                font.pixelSize: 12
                            }
                        }
                        Label {
                            text: "31 JUL 2026  ·  11:24 LOCAL"
                            color: Constants.mutedTextColor
                            font.family: Constants.technicalFont
                            font.pixelSize: 10
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        spacing: 10
                        MetricTile { Layout.fillWidth: true; label: "FLEET READINESS"; value: "85%"; detail: "NOMINAL"; accentColor: Constants.nominalColor }
                        MetricTile { Layout.fillWidth: true; label: "PROBES"; value: "03"; detail: "2 IDLE · 1 ACTIVE" }
                        MetricTile { Layout.fillWidth: true; label: "MANNIES"; value: "08"; detail: "3 AVAILABLE" }
                        MetricTile { Layout.fillWidth: true; label: "ACTIVE OPS"; value: "01"; detail: "0 BLOCKED" }
                        MetricTile { Layout.fillWidth: true; label: "ATTENTION"; value: "01"; detail: "RESOURCE WARNING"; accentColor: Constants.warningColor }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.leftMargin: 18
                        Layout.rightMargin: 18
                        Layout.bottomMargin: 18
                        columns: 12
                        rowSpacing: 14
                        columnSpacing: 14

                        PanelFrame {
                            Layout.columnSpan: 5
                            Layout.fillWidth: true
                            Layout.preferredHeight: 270
                            title: "Focused Probe · Manny One"
                            contentItem: Column {
                                width: parent.width
                                spacing: 9
                                Row {
                                    spacing: 10
                                    StatusPill { label: "IDLE" }
                                    StatusPill { label: "GENERIC"; statusColor: Constants.noticeColor }
                                    Label { anchors.verticalCenter: parent.verticalCenter; text: "FCC  0 / 0 / 0"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
                                }
                                TelemetryBar { width: parent.width; label: "DEUTERIUM"; value: 0.72; reading: "72 / 100" }
                                TelemetryBar { width: parent.width; label: "CARGO UTILIZATION"; value: 0.45; reading: "4.5 / 10"; accentColor: Constants.noticeColor }
                                TelemetryBar { width: parent.width; label: "SYSTEM INTEGRITY"; value: 0.96; reading: "96%"; accentColor: Constants.nominalColor }
                            }
                        }

                        PanelFrame {
                            Layout.columnSpan: 7
                            Layout.fillWidth: true
                            Layout.preferredHeight: 270
                            title: "Live Sector View"
                            contentItem: SectorView { anchors.fill: parent }
                        }

                        PanelFrame {
                            Layout.columnSpan: 12
                            Layout.fillWidth: true
                            Layout.preferredHeight: 145
                            title: "Current Operation"
                            contentItem: RowLayout {
                                width: parent.width
                                Label { text: "EXPAND MINING · METALS"; color: Constants.textColor; font.bold: true; font.pixelSize: 14 }
                                StatusPill { label: "ACTIVE"; statusColor: Constants.noticeColor }
                                Rectangle { Layout.preferredWidth: 1; Layout.preferredHeight: 42; color: Constants.lineColor }
                                Column {
                                    Label { text: "STEP 2 OF 4 · ESTABLISH STORAGE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
                                    Label { text: "NEXT  Assign mining Mannys to MN-184"; color: Constants.mutedTextColor; font.pixelSize: 10 }
                                }
                                ProgressBar { Layout.fillWidth: true; value: 0.43 }
                                Label { text: "ETA 01:42:18"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
                                Button { text: "INSPECT" }
                            }
                        }

                        PanelFrame {
                            Layout.columnSpan: 4
                            Layout.fillWidth: true
                            Layout.preferredHeight: 245
                            title: "Resource Outlook"
                            contentItem: Column {
                                width: parent.width
                                spacing: 10
                                TelemetryBar { width: parent.width; label: "METALS"; value: 0.64; reading: "128.4" }
                                TelemetryBar { width: parent.width; label: "MINERALS"; value: 0.38; reading: "76.0"; accentColor: Constants.noticeColor }
                                TelemetryBar { width: parent.width; label: "DEUTERIUM"; value: 0.19; reading: "38.2"; accentColor: Constants.warningColor }
                                Label { text: "Deuterium source replacement advised"; color: Constants.warningColor; font.pixelSize: 10 }
                            }
                        }

                        PanelFrame {
                            Layout.columnSpan: 4
                            Layout.fillWidth: true
                            Layout.preferredHeight: 245
                            title: "Attention Queue"
                            contentItem: Column {
                                width: parent.width
                                spacing: 10
                                StatusPill { label: "WARNING"; statusColor: Constants.warningColor }
                                Label { width: parent.width; wrapMode: Text.WordWrap; text: "DEUTERIUM FIELD LOW\nAsteroid D-42 has fallen below the configured replacement threshold."; color: Constants.textColor; lineHeight: 1.25 }
                                Label { text: "Replacement source: FCC 2 / 0 / 0"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                                Button { text: "REVIEW PLAN" }
                            }
                        }

                        PanelFrame {
                            Layout.columnSpan: 4
                            Layout.fillWidth: true
                            Layout.preferredHeight: 245
                            title: "Upcoming Events"
                            contentItem: Column {
                                width: parent.width
                                spacing: 11
                                Label { text: "00:04:32  ·  MANNY CRAFT COMPLETE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                                Rectangle { width: parent.width; height: 1; color: Constants.lineColor }
                                Label { text: "00:18:00  ·  DEPOT COLLECTION DUE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                                Rectangle { width: parent.width; height: 1; color: Constants.lineColor }
                                Label { text: "01:42:18  ·  OPERATION STEP ETA"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                                Button { text: "OPEN TIMELINE" }
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
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 18
                anchors.rightMargin: 18
                Label { text: "SNAPSHOT CURRENT"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                Label { text: "·  API v104  ·  AUTOMATION OBSERVE-ONLY"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                Item { Layout.fillWidth: true }
                Label { text: "SKUNKWORKS 0.7.0"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
            }
        }
    }
}
