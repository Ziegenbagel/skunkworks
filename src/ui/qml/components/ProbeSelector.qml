pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root

    property var probeModel: []
    property int currentProbeId: -1
    property bool refreshing: false
    readonly property var selectedProbe: selector.currentIndex >= 0 && selector.currentIndex < probeModel.length ? probeModel[selector.currentIndex] : null

    signal probeSelected(int probeId)
    signal refreshRequested

    implicitWidth: 390
    implicitHeight: 54

    function indexForProbe(probeId) {
        for (let index = 0; index < probeModel.length; ++index) {
            if (Number(probeModel[index].id) === Number(probeId))
                return index;
        }
        return probeModel.length ? 0 : -1;
    }

    onCurrentProbeIdChanged: selector.currentIndex = indexForProbe(currentProbeId)
    onProbeModelChanged: selector.currentIndex = indexForProbe(currentProbeId)

    RowLayout {
        anchors.fill: parent
        spacing: 8

        Image {
            Layout.preferredWidth: 38
            Layout.preferredHeight: 38
            source: root.selectedProbe ? AssetCatalog.probeIcon(root.selectedProbe.model) : AssetCatalog.icon("unknown-object")
            fillMode: Image.PreserveAspectFit
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Label {
                text: "FOCUSED PROBE"
                color: Constants.mutedTextColor
                font.family: Constants.technicalFont
                font.pixelSize: 8
            }

            ComboBox {
                id: selector
                Layout.fillWidth: true
                Layout.preferredHeight: 28
                model: root.probeModel
                textRole: "name"
                valueRole: "id"
                enabled: count > 0 && !root.refreshing

                background: Rectangle {
                    color: selector.pressed ? Constants.selectedColor : Constants.raisedColor
                    border.color: selector.activeFocus ? Constants.cyanColor : Constants.lineColor
                    radius: 2
                }

                contentItem: Label {
                    leftPadding: 9
                    rightPadding: 25
                    text: selector.displayText
                    color: Constants.textColor
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    font.family: Constants.technicalFont
                    font.pixelSize: 10
                }

                indicator: Label {
                    x: selector.width - width - 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: "⌄"
                    color: Constants.cyanColor
                    font.pixelSize: 14
                }

                delegate: ItemDelegate {
                    required property var model
                    required property int index
                    width: selector.width
                    text: model.name + "  ·  " + String(model.status || "unknown").toUpperCase()
                    highlighted: selector.highlightedIndex === index
                }

                onActivated: {
                    const requestedProbeId = Number(currentValue);
                    if (Number.isFinite(requestedProbeId) && requestedProbeId !== root.currentProbeId) {
                        root.probeSelected(requestedProbeId);
                        // Keep the control aligned with the accepted dashboard
                        // while the requested probe snapshot is loading.
                        currentIndex = root.indexForProbe(root.currentProbeId);
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                text: root.selectedProbe ? (String(root.selectedProbe.model || "generic").split("_").join(" ").toUpperCase() + "  ·  " + String(root.selectedProbe.status || "unknown").toUpperCase() + "  ·  " + String(root.selectedProbe.sectorLabel || "SECTOR UNKNOWN")) : "NO PROBES AVAILABLE"
                color: root.selectedProbe && root.selectedProbe.isReachable === false ? Constants.warningColor : Constants.cyanColor
                elide: Text.ElideRight
                font.family: Constants.technicalFont
                font.pixelSize: 8
            }
        }

        ToolButton {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            text: root.refreshing ? "…" : "↻"
            enabled: !root.refreshing
            onClicked: root.refreshRequested()
            ToolTip.visible: hovered
            ToolTip.text: "Refresh focused probe"
        }
    }
}
