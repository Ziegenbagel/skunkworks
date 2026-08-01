pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property bool previewMode: true
    property var sectorData: ({})
    property var focusProbe: ({"name": "Manny One", "model": "generic"})
    readonly property var objectModel: sectorData.objects || []
    readonly property var orbitalBodies: objectModel.filter(item => item.layoutRole === "orbital_body" && item.type !== "star")
    readonly property var stars: objectModel.filter(item => item.layoutRole === "orbital_body" && item.type === "star")
    readonly property var freeObjects: objectModel.filter(item => item.layoutRole !== "orbital_body")
    readonly property real centerX: width * 0.47
    readonly property real centerY: height * 0.50
    property string sectorLabel: "FCC 0 / 0 / 0"

    function orbitRadius(index) {
        const available = Math.min(width * 0.68, height * 0.78);
        return 68 + (index + 1) * Math.max(34, available / Math.max(3, orbitalBodies.length + 1));
    }
    function orbitAngle(index) { return -Math.PI / 2 + index * 0.78; }
    function bodyX(index) { return centerX + Math.cos(orbitAngle(index)) * orbitRadius(index); }
    function bodyY(index) { return centerY + Math.sin(orbitAngle(index)) * orbitRadius(index) * 0.42; }
    function objectIndex(identifier) {
        for (let i = 0; i < orbitalBodies.length; ++i)
            if (String(orbitalBodies[i].id) === String(identifier)) return i;
        return -1;
    }

    color: "#09141c"
    border.color: Constants.lineColor
    clip: true

    Repeater {
        model: root.orbitalBodies
        delegate: Rectangle {
            required property int index
            width: root.orbitRadius(index) * 2
            height: width * 0.42
            x: root.centerX - width / 2
            y: root.centerY - height / 2
            radius: height / 2
            color: "transparent"
            border.color: Qt.rgba(Constants.cyanColor.r, Constants.cyanColor.g, Constants.cyanColor.b, 0.20)
        }
    }

    Rectangle {
        x: root.centerX - 42; y: root.centerY - 42; width: 84; height: 84; radius: 42
        color: Qt.rgba(0.05, 0.20, 0.27, 0.55)
        border.color: Constants.cyanColor
        Image {
            anchors.fill: parent; anchors.margins: 7
            source: AssetCatalog.icon("star")
            fillMode: Image.PreserveAspectFit
        }
        Label {
            anchors.top: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
            text: root.stars.length && root.stars[0].name ? root.stars[0].name : "PRIMARY STAR"
            color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 8
        }
    }

    Repeater {
        model: root.orbitalBodies
        delegate: MapObjectMarker {
            id: orbitalMarker
            required property var modelData
            required property int index
            width: 48; height: 48
            x: root.bodyX(index) - width / 2
            y: root.bodyY(index) - height / 2
            iconSource: modelData.estimated ? AssetCatalog.icon("unknown-object") : AssetCatalog.objectIcon(modelData.type, modelData)
            dimmed: modelData.estimated || root.sectorData.confidence < 0.5
            badgeSources: modelData.isTransitBeacon ? [AssetCatalog.icon("badge-scut-transit-beacon")] : []
            Label {
                anchors.left: parent.right; anchors.leftMargin: 5; anchors.verticalCenter: parent.verticalCenter
                width: 125; elide: Text.ElideRight
                text: (orbitalMarker.index + 1) + " · " + (orbitalMarker.modelData.name || String(orbitalMarker.modelData.type).toUpperCase())
                color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 8
            }
        }
    }

    Repeater {
        model: root.freeObjects
        delegate: MapObjectMarker {
            id: freeMarker
            required property var modelData
            required property int index
            readonly property real angle: -0.55 + index * 0.72
            width: 46; height: 46
            x: root.centerX + Math.cos(angle) * root.width * 0.38 - width / 2
            y: root.centerY + Math.sin(angle) * root.height * 0.38 - height / 2
            iconSource: modelData.estimated ? AssetCatalog.icon("unknown-object") : AssetCatalog.objectIcon(modelData.type, modelData)
            badgeSources: modelData.isTransitBeacon ? [AssetCatalog.icon("badge-scut-transit-beacon")] : []
            Label {
                anchors.left: parent.right; anchors.leftMargin: 5; width: 120
                text: freeMarker.modelData.name || String(freeMarker.modelData.type).toUpperCase()
                color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8; elide: Text.ElideRight
            }
        }
    }

    MapObjectMarker {
        width: 56; height: 56
        x: root.width * 0.17; y: root.height * 0.72
        iconSource: AssetCatalog.probeIcon(root.focusProbe.model || "generic")
        selected: true
        Label {
            anchors.left: parent.right; anchors.leftMargin: 6; anchors.verticalCenter: parent.verticalCenter
            text: root.focusProbe.name || "FOCUSED PROBE"
            color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 8
        }
    }

    Repeater {
        model: root.sectorData.activeMannies || []
        delegate: MapObjectMarker {
            id: mannyMarker
            required property var modelData
            required property int index
            readonly property int targetIndex: root.objectIndex(modelData.targetObjectId)
            width: 34; height: 34
            x: targetIndex >= 0 ? root.bodyX(targetIndex) + 24 : root.width * 0.17 + index * 38
            y: targetIndex >= 0 ? root.bodyY(targetIndex) - 38 : root.height * 0.84
            iconSource: AssetCatalog.icon("manny")
            Label {
                anchors.left: parent.right; anchors.leftMargin: 4; width: 125
                text: mannyMarker.modelData.name + " · " + String(mannyMarker.modelData.task).split("_").join(" ").toUpperCase()
                color: Constants.nominalColor; font.family: Constants.technicalFont; font.pixelSize: 7; elide: Text.ElideRight
            }
        }
    }

    Row {
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 12; spacing: 8
        Image { width: 42; height: 42; source: AssetCatalog.icon("solar-system"); fillMode: Image.PreserveAspectFit }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            Label { text: root.sectorData.system && root.sectorData.system.name ? root.sectorData.system.name : "UNNAMED SYSTEM"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { text: "SYSTEM ID · " + (root.sectorData.system && root.sectorData.system.systemId ? root.sectorData.system.systemId : "UNKNOWN"); color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
        }
    }

    Rectangle {
        visible: Boolean(root.sectorData.emptyReason)
        anchors.centerIn: parent; width: Math.min(parent.width * 0.58, 620); height: 92
        color: Constants.panelColor; border.color: Constants.cyanColor; radius: 3
        Column {
            anchors.centerIn: parent; spacing: 7
            Label { anchors.horizontalCenter: parent.horizontalCenter; text: "EMPTY SECTOR CONFIRMED"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true; font.pixelSize: 12 }
            Label { width: 550; horizontalAlignment: Text.AlignHCenter; text: root.sectorData.emptyReason || ""; color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
        }
    }

    Row {
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 10; spacing: 14
        Label { text: root.sectorData.label || root.sectorLabel; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
        Label {
            text: root.previewMode ? "PREVIEW" : "LIVE · " + String(root.sectorData.knowledgeLevel || "UNKNOWN").toUpperCase() + " · " + Number((root.sectorData.confidence || 0) * 100).toFixed(0) + "% CONFIDENCE"
            color: root.sectorData.confidence >= 0.75 ? Constants.nominalColor : Constants.warningColor
            font.family: Constants.technicalFont; font.pixelSize: 9
        }
        Label { text: "POSITIONS ARE SCHEMATIC · MANNYS ANCHOR TO KNOWN TASK TARGETS"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
    }
}
