pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import ".."

PanelFrame {
    id: root

    property string section: "FLEET"
    property var dashboardData: ({})
    property var availableProbes: []
    property int focusedProbeId: -1
    signal probeSelected(int probeId)

    title: section

    function sectionRows() {
        if (section === "FLEET")
            return availableProbes.map(probe => ({
                        "title": probe.name + (probe.id === focusedProbeId ? "  ·  FOCUSED" : ""),
                        "detail": String(probe.model || "generic").split("_").join(" ").toUpperCase() + "  ·  " + String(probe.status || "unknown").toUpperCase() + "  ·  " + (probe.sectorLabel || "SECTOR UNKNOWN"),
                        "probeId": probe.id
                    }));
        if (section === "RESOURCES")
            return (dashboardData.resources || []).map(item => ({
                        "title": item.label,
                        "detail": item.reading
                    }));
        if (section === "MISSIONS")
            return (dashboardData.missions || []).map(item => ({
                        "title": item.displayText,
                        "detail": item.detailText
                    }));
        if (section === "PRODUCTION")
            return (dashboardData.production || []).map(item => ({
                        "title": item.displayText,
                        "detail": item.detailText
                    }));
        if (section === "SAFETY")
            return (dashboardData.alerts || []).map(item => ({
                        "title": item.codeLabel,
                        "detail": item.summary
                    }));
        if (section === "GALAXY MAP")
            return (dashboardData.sector && dashboardData.sector.objects || []).map(item => ({
                        "title": item.name,
                        "detail": String(item.type).split("_").join(" ").toUpperCase()
                    }));
        if (section === "LOGBOOK")
            return (dashboardData.events || []).map(item => ({
                        "title": String(item.domain || "EVENT").toUpperCase(),
                        "detail": item.observedAt || "Recorded event"
                    }));
        if (section === "SETTINGS")
            return [
                {
                    "title": "CONNECTION",
                    "detail": dashboardData.connectionLabel || "UNKNOWN"
                },
                {
                    "title": "API VERSION",
                    "detail": "v" + (dashboardData.apiVersion || "—")
                },
                {
                    "title": "FOCUSED PROBE",
                    "detail": dashboardData.focus ? dashboardData.focus.name : "None"
                },
                {
                    "title": "AUTOMATION",
                    "detail": "Observe-only"
                }
            ];
        if (section === "RESEARCH")
            return [
                {
                    "title": "RESEARCH INTELLIGENCE",
                    "detail": "No account research endpoint is exposed by API v104. Discovered improvements remain available through probe inspection and safety context."
                }
            ];
        return [];
    }

    contentItem: Item {
        anchors.fill: parent

        Column {
            anchors.fill: parent
            spacing: 12

            Label {
                width: parent.width
                text: root.section === "GALAXY MAP" && root.dashboardData.sector ? "CURRENT OBSERVATION · " + root.dashboardData.sector.label : root.section + " · LIVE ACCOUNT DATA"
                color: Constants.cyanColor
                font.family: Constants.technicalFont
                font.pixelSize: 10
            }

            Rectangle {
                width: parent.width
                height: 1
                color: Constants.lineColor
            }

            ScrollView {
                width: parent.width
                height: parent.height - 42
                clip: true

                ListView {
                    id: sectionList
                    model: root.sectionRows()
                    spacing: 8

                    delegate: Rectangle {
                        id: sectionRow
                        required property var modelData
                        required property int index
                        width: sectionList.width
                        height: detailsColumn.implicitHeight + 24
                        color: rowMouse.containsMouse ? Constants.selectedColor : index % 2 ? Constants.panelColor : Constants.raisedColor
                        border.color: modelData.probeId === root.focusedProbeId ? Constants.cyanColor : Constants.lineColor
                        radius: 2

                        Column {
                            id: detailsColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12
                            spacing: 6

                            Label {
                                width: parent.width
                                text: sectionRow.modelData.title || "No data"
                                color: Constants.textColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 11
                                font.bold: true
                                wrapMode: Text.Wrap
                            }
                            Label {
                                width: parent.width
                                text: sectionRow.modelData.detail || ""
                                color: Constants.mutedTextColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                            }
                        }

                        MouseArea {
                            id: rowMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: sectionRow.modelData.probeId !== undefined
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: root.probeSelected(Number(sectionRow.modelData.probeId))
                        }
                    }

                    Label {
                        visible: sectionList.count === 0
                        anchors.centerIn: parent
                        text: "No live " + root.section.toLowerCase() + " records are currently available."
                        color: Constants.mutedTextColor
                        font.family: Constants.technicalFont
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
