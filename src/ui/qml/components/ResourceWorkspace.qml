pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var ledgerData: ({})
    readonly property var categories: [
        {"key": "probe", "title": "PROBE STORAGE", "description": "Resources aboard the selected probe, separated by storage container."},
        {"key": "drifting", "title": "DRIFTING CONTAINERS", "description": "Visible detached containers floating in the current sector."},
        {"key": "placed", "title": "PLACED CONTAINERS", "description": "Visible containers attached to asteroids or other sector objects."},
        {"key": "asteroid", "title": "ASTEROID CONTENTS", "description": "Authoritative remaining mineable reserves from the latest detailed scan."},
        {"key": "planet", "title": "PLANETARY RESOURCES", "description": "Remaining mineable resources on observed planets."},
        {"key": "other", "title": "OTHER RESOURCE SOURCES", "description": "Other observed natural resource sources."}
    ]

    function categoryFor(row) {
        if (row.scope === "probe_storage") return "probe";
        if (row.scope === "detached_container")
            return String(row.detail || "").indexOf("Floating in sector") >= 0 ? "drifting" : "placed";
        const sourceType = String(row.sourceType || "").toLowerCase();
        if (sourceType === "asteroid") return "asteroid";
        if (sourceType === "planet") return "planet";
        return "other";
    }

    function rowsFor(key) {
        return (ledgerData.rows || []).filter(row => categoryFor(row) === key);
    }

    ScrollView {
        anchors.fill: parent
        clip: true

        ColumnLayout {
            width: root.width - 20
            spacing: 20

            Label {
                text: "SECTOR RESOURCE LEDGER"
                color: Constants.cyanColor
                font.family: Constants.displayFont
                font.pixelSize: 18
                font.bold: true
                font.letterSpacing: 1.2
            }
            Label {
                Layout.fillWidth: true
                text: "Storage and remaining natural reserves visible to the selected probe. Amounts are in equivalent Earth containers unless marked as a percentage."
                color: Constants.mutedTextColor
                font.family: Constants.bodyFont
                font.pixelSize: 14
                wrapMode: Text.Wrap
            }

            Repeater {
                model: root.categories
                delegate: ColumnLayout {
                    id: categorySection
                    required property var modelData
                    readonly property var rows: root.rowsFor(modelData.key)
                    visible: rows.length > 0
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        text: categorySection.modelData.title + "  ·  " + categorySection.rows.length
                        color: Constants.cyanColor
                        font.family: Constants.technicalFont
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Label {
                        Layout.fillWidth: true
                        text: categorySection.modelData.description
                        color: Constants.mutedTextColor
                        font.family: Constants.bodyFont
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                    }
                    GridLayout {
                        id: resourceGrid
                        Layout.fillWidth: true
                        columns: width >= 1400 ? 3 : width >= 850 ? 2 : 1
                        columnSpacing: 18
                        rowSpacing: 18

                        Repeater {
                            model: categorySection.rows
                            delegate: Rectangle {
                                id: resourceCard
                                required property var modelData
                                Layout.preferredWidth: (categorySection.width - (resourceGrid.columns - 1) * resourceGrid.columnSpacing) / resourceGrid.columns
                                Layout.minimumWidth: 420
                                implicitHeight: resourceText.implicitHeight + 38
                                color: Constants.raisedColor
                                border.color: Constants.lineColor
                                radius: 4

                                ColumnLayout {
                                    id: resourceText
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 10
                                    Label {
                                        Layout.fillWidth: true
                                        text: resourceCard.modelData.title || "Unknown resource"
                                        color: Constants.textColor
                                        font.family: Constants.technicalFont
                                        font.pixelSize: 17
                                        font.bold: true
                                        wrapMode: Text.Wrap
                                    }
                                    Label {
                                        Layout.fillWidth: true
                                        text: resourceCard.modelData.detail || ""
                                        color: Constants.mutedTextColor
                                        font.family: Constants.bodyFont
                                        font.pixelSize: 15
                                        lineHeight: 1.3
                                        wrapMode: Text.Wrap
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Constants.lineColor; visible: (root.ledgerData.notes || []).length > 0 }
            Label { text: "DATA COVERAGE"; visible: (root.ledgerData.notes || []).length > 0; color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 14; font.bold: true }
            Repeater {
                model: root.ledgerData.notes || []
                delegate: Label {
                    required property var modelData
                    Layout.fillWidth: true
                    text: "• " + modelData
                    color: Constants.mutedTextColor
                    font.family: Constants.bodyFont
                    font.pixelSize: 13
                    wrapMode: Text.Wrap
                }
            }
        }
    }
}
