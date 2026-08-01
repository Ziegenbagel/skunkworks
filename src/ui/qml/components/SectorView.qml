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
    readonly property var orbitalBodies: objectModel.filter(item => item.layoutRole === "orbital_body" && (String(item.type).toLowerCase() === "planet" || String(item.type).toLowerCase().endsWith("_planet")))
    readonly property var stars: objectModel.filter(item => item.layoutRole === "orbital_body" && item.type === "star")
    readonly property var freeObjects: objectModel.filter(item => item.type !== "star" && !(item.layoutRole === "orbital_body" && (String(item.type).toLowerCase() === "planet" || String(item.type).toLowerCase().endsWith("_planet"))))
    readonly property var mannyClusters: buildMannyClusters(sectorData.activeMannies || [])
    readonly property int maximumMannyAreas: 12
    readonly property real centerX: width * 0.50
    readonly property real centerY: height * 0.50
    readonly property real orbitAspect: 0.52
    property string sectorLabel: "FCC 0 / 0 / 0"

    function orbitRadius(index) {
        const minimumRadius = 96;
        const maximumRadius = Math.max(150, Math.min(width * 0.34, height * 0.38 / orbitAspect));
        if (orbitalBodies.length <= 1)
            return Math.min(maximumRadius, minimumRadius * 1.45);
        return minimumRadius + index * (maximumRadius - minimumRadius) / (orbitalBodies.length - 1);
    }
    function orbitAngle(index) { return -Math.PI / 2 + index * 0.78; }
    function bodyX(index) { return centerX + Math.cos(orbitAngle(index)) * orbitRadius(index); }
    function bodyY(index) { return centerY + Math.sin(orbitAngle(index)) * orbitRadius(index) * orbitAspect; }
    function objectIndex(identifier) {
        for (let i = 0; i < orbitalBodies.length; ++i)
            if (String(orbitalBodies[i].id) === String(identifier)) return i;
        return -1;
    }
    function freeObjectIndex(identifier) {
        for (let i = 0; i < freeObjects.length; ++i)
            if (String(freeObjects[i].id) === String(identifier)) return i;
        return -1;
    }
    function freeAngle(index) { return -0.55 + index * 0.72; }
    function freeObjectX(index) { return centerX + Math.cos(freeAngle(index)) * width * 0.43; }
    function freeObjectY(index) { return centerY + Math.sin(freeAngle(index)) * height * 0.42; }
    function placeLabelOnLeft(markerCenterX) { return markerCenterX > width * 0.72; }
    function buildMannyClusters(mannies) {
        const groups = {};
        const order = [];
        for (let i = 0; i < mannies.length; ++i) {
            const manny = mannies[i];
            const targetId = manny.targetObjectId ? String(manny.targetObjectId) : "focused-probe";
            const task = String(manny.task || "active").split("_").join(" ").toUpperCase();
            const key = targetId;
            if (!groups[key]) {
                groups[key] = { "targetObjectId": targetId, "task": task, "count": 0 };
                order.push(key);
            } else if (groups[key].task !== task) {
                groups[key].task = "MULTIPLE TASKS";
            }
            groups[key].count += 1;
        }
        return order.map(key => groups[key]);
    }

    color: "#09141c"
    border.color: Constants.lineColor
    clip: true

    Repeater {
        model: root.orbitalBodies
        delegate: Canvas {
            id: orbitCanvas
            required property int index
            anchors.fill: parent
            opacity: 0.28
            onPaint: {
                const context = getContext("2d");
                context.reset();
                context.strokeStyle = Constants.cyanColor;
                context.lineWidth = 1.25;
                context.beginPath();
                const horizontalRadius = root.orbitRadius(index);
                const verticalRadius = horizontalRadius * root.orbitAspect;
                // Qt Quick Canvas uses ellipse(x, y, width, height), where x/y
                // are the bounding rectangle's upper-left corner.
                context.ellipse(root.centerX - horizontalRadius,
                                root.centerY - verticalRadius,
                                horizontalRadius * 2,
                                verticalRadius * 2);
                context.stroke();
            }
            Connections {
                target: root
                function onWidthChanged() { orbitCanvas.requestPaint(); }
                function onHeightChanged() { orbitCanvas.requestPaint(); }
            }
        }
    }

    Rectangle {
        x: root.centerX - 58; y: root.centerY - 58; width: 116; height: 116; radius: 58
        color: Qt.rgba(0.05, 0.20, 0.27, 0.55)
        border.color: Constants.cyanColor
        Image {
            anchors.fill: parent; anchors.margins: 8
            source: AssetCatalog.icon("star")
            fillMode: Image.PreserveAspectFit
        }
        Label {
            anchors.top: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
            text: root.stars.length && root.stars[0].name ? root.stars[0].name : "PRIMARY STAR"
            color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 14; font.bold: true
        }
    }

    Repeater {
        model: root.orbitalBodies
        delegate: MapObjectMarker {
            id: orbitalMarker
            required property var modelData
            required property int index
            width: 80; height: 80
            x: root.bodyX(index) - width / 2
            y: root.bodyY(index) - height / 2
            iconSource: modelData.estimated ? AssetCatalog.icon("unknown-object") : AssetCatalog.objectIcon(modelData.type, modelData)
            dimmed: modelData.estimated || root.sectorData.confidence < 0.5
            badgeSources: modelData.isTransitBeacon ? [AssetCatalog.icon("badge-scut-transit-beacon")] : []
            Label {
                readonly property bool verticalLabel: orbitalMarker.index === 0 || orbitalMarker.index === root.orbitalBodies.length - 1
                anchors.left: verticalLabel ? undefined : parent.right
                anchors.leftMargin: verticalLabel ? 0 : 9
                anchors.top: orbitalMarker.index === 0 ? parent.bottom : undefined
                anchors.topMargin: orbitalMarker.index === 0 ? 5 : 0
                anchors.bottom: orbitalMarker.index === root.orbitalBodies.length - 1 ? parent.top : undefined
                anchors.bottomMargin: orbitalMarker.index === root.orbitalBodies.length - 1 ? 5 : 0
                anchors.horizontalCenter: verticalLabel ? parent.horizontalCenter : undefined
                anchors.verticalCenter: verticalLabel ? undefined : parent.verticalCenter
                width: 190; elide: Text.ElideRight
                horizontalAlignment: verticalLabel ? Text.AlignHCenter : Text.AlignLeft
                text: (orbitalMarker.index + 1) + " · " + (orbitalMarker.modelData.name || String(orbitalMarker.modelData.type).toUpperCase())
                color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 14; font.bold: true
            }
        }
    }

    Repeater {
        model: root.freeObjects
        delegate: MapObjectMarker {
            id: freeMarker
            required property var modelData
            required property int index
            width: 72; height: 72
            x: root.freeObjectX(index) - width / 2
            y: root.freeObjectY(index) - height / 2
            iconSource: modelData.estimated ? AssetCatalog.icon("unknown-object") : AssetCatalog.objectIcon(modelData.type, modelData)
            badgeSources: modelData.isTransitBeacon ? [AssetCatalog.icon("badge-scut-transit-beacon")] : []
            Label {
                readonly property bool onLeft: root.placeLabelOnLeft(root.freeObjectX(freeMarker.index))
                anchors.left: onLeft ? undefined : parent.right
                anchors.leftMargin: onLeft ? 0 : 9
                anchors.right: onLeft ? parent.left : undefined
                anchors.rightMargin: onLeft ? 9 : 0
                anchors.verticalCenter: parent.verticalCenter
                width: 185
                horizontalAlignment: onLeft ? Text.AlignRight : Text.AlignLeft
                text: freeMarker.modelData.name || String(freeMarker.modelData.type).toUpperCase()
                color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 13; font.bold: true; elide: Text.ElideRight
            }
        }
    }

    MapObjectMarker {
        width: 88; height: 88
        x: root.width * 0.10; y: root.height * 0.70
        iconSource: AssetCatalog.probeIcon(root.focusProbe.model || "generic")
        selected: true
        Label {
            anchors.left: parent.right; anchors.leftMargin: 6; anchors.verticalCenter: parent.verticalCenter
            text: root.focusProbe.name || "FOCUSED PROBE"
            color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 14; font.bold: true
        }
    }

    Repeater {
        model: root.mannyClusters.slice(0, root.maximumMannyAreas)
        delegate: MapObjectMarker {
            id: mannyMarker
            required property var modelData
            required property int index
            readonly property int targetIndex: root.objectIndex(modelData.targetObjectId)
            readonly property int freeTargetIndex: root.freeObjectIndex(modelData.targetObjectId)
            readonly property bool targetsFocusedProbe: modelData.targetObjectId === "focused-probe"
            readonly property real targetX: targetIndex >= 0 ? root.bodyX(targetIndex)
                                                 : freeTargetIndex >= 0 ? root.freeObjectX(freeTargetIndex)
                                                 : root.width * 0.10
            readonly property real targetY: targetIndex >= 0 ? root.bodyY(targetIndex)
                                                 : freeTargetIndex >= 0 ? root.freeObjectY(freeTargetIndex)
                                                 : root.height * 0.70
            readonly property bool placeInward: root.placeLabelOnLeft(targetX)
            width: 46; height: 46
            x: targetIndex >= 0 || freeTargetIndex >= 0 ? (placeInward ? targetX - 78 : targetX + 32)
               : targetsFocusedProbe ? root.width * 0.10 + 102
               : root.width * 0.10 + (index % 4) * 170
            y: targetIndex >= 0 || freeTargetIndex >= 0 ? Math.min(root.height - 88, targetY + 34)
               : targetsFocusedProbe ? root.height * 0.70 + 54
               : root.height * 0.82 + Math.floor(index / 4) * 46
            iconSource: AssetCatalog.icon("manny")
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.bottom
                anchors.topMargin: 1
                width: Math.min(150, mannyLabel.implicitWidth + 12)
                height: 22
                radius: 3
                color: Qt.rgba(0.04, 0.12, 0.16, 0.92)
                border.color: Qt.rgba(Constants.nominalColor.r, Constants.nominalColor.g, Constants.nominalColor.b, 0.45)
                Label {
                    id: mannyLabel
                    anchors.centerIn: parent
                    width: Math.min(138, implicitWidth)
                    horizontalAlignment: Text.AlignHCenter
                text: "×" + mannyMarker.modelData.count + " · " + mannyMarker.modelData.task
                    color: Constants.nominalColor; font.family: Constants.technicalFont; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight
                }
            }
        }
    }

    Label {
        visible: root.mannyClusters.length > root.maximumMannyAreas
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: 14
        anchors.bottomMargin: 34
        text: "+" + (root.mannyClusters.length - root.maximumMannyAreas) + " MORE MANNY WORK AREAS"
        color: Constants.warningColor
        font.family: Constants.technicalFont
        font.pixelSize: 11
        font.bold: true
    }

    Row {
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 12; spacing: 8
        Image { width: 58; height: 58; source: AssetCatalog.icon("solar-system"); fillMode: Image.PreserveAspectFit }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            Label { text: root.sectorData.system && root.sectorData.system.name ? root.sectorData.system.name : "UNNAMED SYSTEM"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
            Label { text: "SYSTEM ID · " + (root.sectorData.system && root.sectorData.system.systemId ? root.sectorData.system.systemId : "UNKNOWN"); color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
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
        Label { text: root.sectorData.label || root.sectorLabel; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 11; font.bold: true }
        Label {
            text: root.previewMode ? "PREVIEW" : "LIVE · " + String(root.sectorData.knowledgeLevel || "UNKNOWN").toUpperCase() + " · " + Number((root.sectorData.confidence || 0) * 100).toFixed(0) + "% CONFIDENCE"
            color: root.sectorData.confidence >= 0.75 ? Constants.nominalColor : Constants.warningColor
            font.family: Constants.technicalFont; font.pixelSize: 11; font.bold: true
        }
        Label { text: root.orbitalBodies.length + " PLANET" + (root.orbitalBodies.length === 1 ? "" : "S") + " · ONE ORBIT PER PLANET · MANNYS ANCHOR TO KNOWN TASK TARGETS"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 10 }
    }
}
