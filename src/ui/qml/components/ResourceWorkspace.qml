pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root
    property var ledgerData: ({})
    signal unusualMiningTargetApprovalRequested(string targetId, bool approved)
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
        id: resourceScroll
        anchors.fill: parent
        clip: true

        Column {
            width: resourceScroll.availableWidth
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
                width: parent.width
                text: "Storage and remaining natural reserves visible to the selected probe. Amounts are in equivalent Earth containers unless marked as a percentage."
                color: Constants.mutedTextColor
                font.family: Constants.bodyFont
                font.pixelSize: 14
                wrapMode: Text.Wrap
            }

            Repeater {
                model: root.categories
                delegate: Column {
                    id: categorySection
                    required property var modelData
                    readonly property var rows: root.rowsFor(modelData.key)
                    visible: rows.length > 0
                    width: parent.width
                    height: visible ? implicitHeight : 0
                    spacing: 8

                    Label {
                        text: categorySection.modelData.title + "  ·  " + categorySection.rows.length
                        color: Constants.cyanColor
                        font.family: Constants.technicalFont
                        font.pixelSize: 15
                        font.bold: true
                    }
                    Label {
                        width: parent.width
                        text: categorySection.modelData.description
                        color: Constants.mutedTextColor
                        font.family: Constants.bodyFont
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                    }
                    Grid {
                        id: resourceGrid
                        width: parent.width
                        columns: width >= 1400 ? 3 : width >= 850 ? 2 : 1
                        spacing: 18

                        Repeater {
                            model: categorySection.rows
                            delegate: Rectangle {
                                id: resourceCard
                                required property var modelData
                                width: (resourceGrid.width - (resourceGrid.columns - 1) * resourceGrid.spacing) / resourceGrid.columns
                                height: resourceText.implicitHeight + 38
                                color: Constants.raisedColor
                                border.color: Constants.lineColor
                                radius: 4

                                Column {
                                    id: resourceText
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.top: parent.top
                                    anchors.margins: 18
                                    spacing: 10
                                    Label {
                                        width: parent.width
                                        text: resourceCard.modelData.title || "Unknown resource"
                                        color: Constants.textColor
                                        font.family: Constants.technicalFont
                                        font.pixelSize: 17
                                        font.bold: true
                                        wrapMode: Text.Wrap
                                    }
                                    Label {
                                        width: parent.width
                                        text: resourceCard.modelData.detail || ""
                                        color: Constants.mutedTextColor
                                        font.family: Constants.bodyFont
                                        font.pixelSize: 15
                                        lineHeight: 1.3
                                        wrapMode: Text.Wrap
                                    }
                                    Button {
                                        visible: Boolean(resourceCard.modelData.requiresAutomationApproval)
                                        text: resourceCard.modelData.automationApproved ? "REVOKE AUTOMATION APPROVAL" : "APPROVE FOR MINING AUTOMATION"
                                        onClicked: root.unusualMiningTargetApprovalRequested(String(resourceCard.modelData.objectId), !Boolean(resourceCard.modelData.automationApproved))
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: Constants.lineColor; visible: (root.ledgerData.notes || []).length > 0 }
            Label { text: "DATA COVERAGE"; visible: (root.ledgerData.notes || []).length > 0; color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 14; font.bold: true }
            Repeater {
                model: root.ledgerData.notes || []
                delegate: Label {
                    required property var modelData
                    width: parent.width
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
