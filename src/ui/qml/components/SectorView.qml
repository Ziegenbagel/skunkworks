pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property bool previewMode: true
    property var sectorData: ({})
    property var focusProbe: ({
            "name": "Manny One",
            "model": "generic"
        })
    readonly property var previewObjects: [
        {
            "id": "preview-resource",
            "type": "asteroid",
            "name": "D-42 · Deuterium",
            "resources": {
                "deuterium": 482
            }
        },
        {
            "id": "preview-depot",
            "type": "detached_container",
            "name": "Depot MN-184"
        },
        {
            "id": "preview-world",
            "type": "planet",
            "category": "ocean",
            "name": "Ocean world"
        }
    ]
    readonly property var objectModel: previewMode ? previewObjects : (sectorData.objects || [])
    property string sectorLabel: "FCC 0 / 0 / 0"
    color: "#09141c"
    border.color: Constants.lineColor
    clip: true

    Repeater {
        model: [0.28, 0.52, 0.76]
        delegate: Rectangle {
            required property real modelData
            width: Math.min(root.width, root.height) * modelData
            height: width
            anchors.centerIn: parent
            radius: width / 2
            color: "transparent"
            border.color: Qt.rgba(Constants.cyanColor.r, Constants.cyanColor.g, Constants.cyanColor.b, 0.22)
            border.width: 1
        }
    }

    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        width: 1
        height: parent.height
        color: Qt.rgba(0.33, 0.78, 0.85, 0.18)
    }
    Rectangle {
        anchors.verticalCenter: parent.verticalCenter
        height: 1
        width: parent.width
        color: Qt.rgba(0.33, 0.78, 0.85, 0.18)
    }

    ScutNetworkOverlay {
        visible: root.previewMode
        anchors.fill: parent
        anchors.margins: Math.max(18, Math.min(parent.width, parent.height) * 0.06)
        opacity: 0.72
    }

    MapObjectMarker {
        anchors.centerIn: parent
        width: 64
        height: 64
        iconSource: AssetCatalog.probeIcon(root.focusProbe.model || "generic")
        selected: true
        Label {
            anchors.left: parent.right
            anchors.leftMargin: 7
            anchors.verticalCenter: parent.verticalCenter
            text: root.focusProbe.name || "FOCUSED PROBE"
            color: Constants.textColor
            font.family: Constants.technicalFont
            font.pixelSize: 8
        }
    }

    Repeater {
        model: root.objectModel
        delegate: MapObjectMarker {
            id: marker
            required property var modelData
            required property int index
            readonly property real angle: (Math.PI * 2 * index / Math.max(1, root.objectModel.length)) - Math.PI / 2
            width: modelData.type === "solar_system" ? 82 : 62
            height: width
            x: root.width * 0.5 + Math.cos(angle) * root.width * 0.32 - width / 2
            y: root.height * 0.5 + Math.sin(angle) * root.height * 0.32 - height / 2
            iconSource: modelData.estimated ? AssetCatalog.icon("unknown-object") : AssetCatalog.objectIcon(modelData.type, modelData)
            dimmed: modelData.estimated || root.sectorData.confidence < 0.5
            badgeSources: modelData.isTransitBeacon ? [AssetCatalog.icon("badge-scut-transit-beacon")] : []

            Label {
                anchors.left: parent.right
                anchors.leftMargin: 7
                anchors.verticalCenter: parent.verticalCenter
                width: 150
                text: marker.modelData.name || String(marker.modelData.type || "unknown").toUpperCase()
                color: marker.modelData.dangerLevel === "high" ? Constants.criticalColor : Constants.textColor
                elide: Text.ElideRight
                font.family: Constants.technicalFont
                font.pixelSize: 8
            }
        }
    }

    Row {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 10
        spacing: 14
        Label {
            text: root.sectorData.label || root.sectorLabel
            color: Constants.cyanColor
            font.family: Constants.technicalFont
            font.pixelSize: 9
        }
        Label {
            text: root.previewMode ? "PREVIEW · DETAILED" : "LIVE · " + String(root.sectorData.knowledgeLevel || "UNKNOWN").toUpperCase() + " · " + Number((root.sectorData.confidence || 0) * 100).toFixed(0) + "% CONFIDENCE"
            color: root.previewMode || root.sectorData.confidence >= 0.75 ? Constants.nominalColor : Constants.warningColor
            font.family: Constants.technicalFont
            font.pixelSize: 9
        }
    }
}
