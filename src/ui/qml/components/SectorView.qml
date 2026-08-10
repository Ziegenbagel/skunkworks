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
    readonly property var relayObjects: objectModel.filter(item => String(item.type).toLowerCase() === "scut_relay")
    readonly property var freeObjects: objectModel.filter(item => item.type !== "star" && String(item.type).toLowerCase() !== "scut_relay" && !(item.layoutRole === "orbital_body" && (String(item.type).toLowerCase() === "planet" || String(item.type).toLowerCase().endsWith("_planet"))))
    readonly property var mannyClusters: buildMannyClusters(sectorData.activeMannies || [])
    readonly property int maximumMannyAreas: 12
    readonly property int maximumFreeObjects: 8
    readonly property real centerX: width * 0.50
    readonly property real centerY: height * 0.50
    readonly property real orbitAspect: 0.62
    property string sectorLabel: "FCC 0 / 0 / 0"
    property double currentEpochMs: Date.now()
    readonly property bool probeInTransit: ["preparing", "accelerating", "cruising", "decelerating", "traveling"].indexOf(String(focusProbe.status || "").toLowerCase()) >= 0
    readonly property bool blackHoleDanger: Boolean(sectorData.blackHoleDanger)
    function headingLabel(value) { return value && typeof value === "object" ? [value.x || 0, value.y || 0, value.z || 0].join(":") : String(value || "—"); }
    function remainingLabel(movement) {
        if (Number(movement.arrivalEpochMs || 0) > 0) {
            const seconds = Math.max(0, Math.floor((Number(movement.arrivalEpochMs) - root.currentEpochMs) / 1000));
            return Math.floor(seconds / 60) + " MIN " + (seconds % 60) + " S";
        }
        const raw = movement.remainingTime;
        if (raw !== undefined && raw !== null) {
            if (typeof raw === "number") { const seconds = Math.max(0, Math.floor(raw)); return Math.floor(seconds / 60) + " MIN " + (seconds % 60) + " S"; }
            return String(raw);
        }
        if (movement.estimatedArrival) { const seconds = Math.max(0, Math.floor((Date.parse(movement.estimatedArrival) - Date.now()) / 1000)); if (!isNaN(seconds)) return Math.floor(seconds / 60) + " MIN " + (seconds % 60) + " S"; }
        return "AWAITING TELEMETRY";
    }
    function destructionCountdown() {
        const deadline = Number(root.sectorData.destructionEpochMs || 0);
        if (deadline <= 0) return "COUNTDOWN TELEMETRY UNAVAILABLE";
        const seconds = Math.max(0, Math.floor((deadline - root.currentEpochMs) / 1000));
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainder = seconds % 60;
        return (hours > 0 ? hours + " HR " : "") + minutes + " MIN " + remainder + " S";
    }

    Timer {
        interval: 1000
        running: root.visible && (root.probeInTransit || root.blackHoleDanger)
        repeat: true
        triggeredOnStart: true
        onTriggered: root.currentEpochMs = Date.now()
    }

    function orbitRadius(index) {
        const minimumRadius = 170;
        const maximumRadius = Math.max(150, Math.min(width * 0.34, height * 0.38 / orbitAspect));
        if (orbitalBodies.length <= 1)
            return Math.min(maximumRadius, minimumRadius * 1.45);
        return minimumRadius + index * (maximumRadius - minimumRadius) / (orbitalBodies.length - 1);
    }
    function stableRotation() {
        const identifier = String((sectorData.system || {}).systemId || sectorData.label || "sector");
        let hash = 0;
        for (let i = 0; i < identifier.length; ++i)
            hash = ((hash * 31) + identifier.charCodeAt(i)) & 0x7fffffff;
        return (hash % 628) / 100;
    }
    function orbitAngle(index) {
        const irregularAngles = [-1.34, 0.42, 2.76, -2.58, 1.48, -0.18, 3.08, -1.96];
        return irregularAngles[index % irregularAngles.length] + stableRotation();
    }
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
    function relayObjectIndex(identifier) {
        for (let i = 0; i < relayObjects.length; ++i)
            if (String(relayObjects[i].id) === String(identifier)) return i;
        return -1;
    }
    function freeObjectX(index) {
        const edgeBuffer = 46;
        return index < 3 ? edgeBuffer : width - edgeBuffer;
    }
    function freeObjectY(index) {
        const leftRows = [0.20, 0.40, 0.60];
        const rightRows = [0.20, 0.35, 0.50, 0.65, 0.80];
        return height * (index < 3 ? leftRows[index] : rightRows[index - 3]);
    }
    function relayObjectX(index) { return width - 62; }
    function relayObjectY(index) { return height - 112 - Math.min(index, 2) * 78; }
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

    onBlackHoleDangerChanged: if (blackHoleDanger) AudioManager.play("warning")
    Component.onCompleted: if (blackHoleDanger) AudioManager.play("warning")

    Rectangle {
        id: blackHoleAlert
        visible: root.blackHoleDanger
        z: 1100
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.topMargin: 22
        width: Math.min(parent.width - 44, 820)
        height: 112
        color: Qt.rgba(0.24, 0.01, 0.02, 0.94)
        border.color: Constants.criticalColor
        border.width: 3
        radius: 4
        Column {
            anchors.centerIn: parent; spacing: 8
            Label { anchors.horizontalCenter: parent.horizontalCenter; text: "⚠  BLACK HOLE RED ALERT  ⚠"; color: Constants.criticalColor; font.family: Constants.displayFont; font.pixelSize: 26; font.bold: true }
            Label { anchors.horizontalCenter: parent.horizontalCenter; text: "PROBE DESTRUCTION · " + root.destructionCountdown(); color: "#ffb0b0"; font.family: Constants.technicalFont; font.pixelSize: 18; font.bold: true }
        }
        SequentialAnimation on opacity {
            running: blackHoleAlert.visible; loops: Animation.Infinite
            NumberAnimation { to: 0.42; duration: 1300; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.0; duration: 1300; easing.type: Easing.InOutSine }
        }
    }

    Rectangle {
        visible: root.probeInTransit
        z: 1000
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.margins: 22
        width: Math.min(parent.width - 44, 680)
        height: transitColumn.implicitHeight + 30
        color: Qt.rgba(0.02, 0.07, 0.10, 0.94)
        border.color: Constants.cyanColor
        radius: 4
        Column {
            id: transitColumn
            anchors.fill: parent
            anchors.margins: 15
            spacing: 7
            Label { text: "PROBE IN TRANSIT · " + String(root.focusProbe.status || "traveling").toUpperCase(); color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 22; font.bold: true }
            Label { width: parent.width; text: "ORIGIN SECTOR · " + String((root.focusProbe.movement || {}).originLabel || "UNKNOWN") + "    ARRIVAL SECTOR · " + String((root.focusProbe.movement || {}).destinationLabel || "UNKNOWN"); color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 16; wrapMode: Text.Wrap }
            Label { width: parent.width; text: "SENSORS · " + String(root.focusProbe.sensorMode || "UNKNOWN").toUpperCase() + "    DEUTERIUM · " + Number(root.focusProbe.fuelPercent || 0).toFixed(2) + "%    VELOCITY C · " + String((root.focusProbe.movement || {}).velocity || root.focusProbe.velocity || "—") + "    HEADING · " + root.headingLabel((root.focusProbe.movement || {}).heading); color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 14; wrapMode: Text.Wrap }
            Label { width: parent.width; text: "REMAINING TIME · " + root.remainingLabel(root.focusProbe.movement || ({})); color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true; wrapMode: Text.Wrap }
        }
    }

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

    Item {
        x: root.centerX - 58; y: root.centerY - 58; width: 116; height: 116
        Image {
            anchors.fill: parent; anchors.margins: 5
            source: AssetCatalog.icon("star-v2")
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
                readonly property real angle: root.orbitAngle(orbitalMarker.index)
                readonly property bool nearBottomEdge: root.bodyY(orbitalMarker.index) > root.height - 112
                readonly property bool above: Math.sin(angle) < -0.55 || nearBottomEdge
                readonly property bool below: Math.sin(angle) > 0.55 && !nearBottomEdge
                readonly property bool leftSide: Math.cos(angle) < 0
                anchors.top: below ? parent.bottom : undefined
                anchors.topMargin: below ? 6 : 0
                anchors.bottom: above ? parent.top : undefined
                anchors.bottomMargin: above ? 6 : 0
                anchors.left: !above && !below && !leftSide ? parent.right : undefined
                anchors.leftMargin: 9
                anchors.right: !above && !below && leftSide ? parent.left : undefined
                anchors.rightMargin: 9
                anchors.horizontalCenter: above || below ? parent.horizontalCenter : undefined
                anchors.verticalCenter: above || below ? undefined : parent.verticalCenter
                width: 170; elide: Text.ElideRight
                horizontalAlignment: above || below ? Text.AlignHCenter : leftSide ? Text.AlignRight : Text.AlignLeft
                text: (orbitalMarker.index + 1) + " · " + (orbitalMarker.modelData.name || String(orbitalMarker.modelData.type).toUpperCase())
                color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 14; font.bold: true
            }
        }
    }

    Repeater {
        model: root.freeObjects.slice(0, root.maximumFreeObjects)
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

    Repeater {
        model: root.relayObjects.slice(0, 3)
        delegate: MapObjectMarker {
            id: relayMarker
            required property var modelData
            required property int index
            width: 76; height: 76
            x: root.relayObjectX(index) - width / 2
            y: root.relayObjectY(index) - height / 2
            iconSource: AssetCatalog.objectIcon(modelData.type, modelData)
            badgeSources: modelData.isTransitBeacon ? [AssetCatalog.icon("badge-scut-transit-beacon")] : []
            Label {
                anchors.right: parent.left; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                width: 235; horizontalAlignment: Text.AlignRight; elide: Text.ElideRight
                text: relayMarker.modelData.isTransitBeacon ? "SCUT RELAY · TRANSIT BEACON" : (relayMarker.modelData.name || "SCUT RELAY")
                color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 13; font.bold: true
            }
        }
    }

    Label {
        visible: root.freeObjects.length > root.maximumFreeObjects
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: 14
        anchors.topMargin: 82
        text: "+" + (root.freeObjects.length - root.maximumFreeObjects) + " MORE SECTOR OBJECTS · OPEN RESOURCES FOR DETAILS"
        color: Constants.warningColor
        font.family: Constants.technicalFont
        font.pixelSize: 11
        font.bold: true
    }

    MapObjectMarker {
        width: 88; height: 88
        x: 12; y: root.height * 0.80
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
            readonly property int relayTargetIndex: root.relayObjectIndex(modelData.targetObjectId)
            readonly property bool targetsFocusedProbe: modelData.targetObjectId === "focused-probe"
            readonly property real targetX: targetIndex >= 0 ? root.bodyX(targetIndex)
                                                 : freeTargetIndex >= 0 ? root.freeObjectX(freeTargetIndex)
                                                 : relayTargetIndex >= 0 ? root.relayObjectX(relayTargetIndex)
                                                 : root.width * 0.10
            readonly property real targetY: targetIndex >= 0 ? root.bodyY(targetIndex)
                                                 : freeTargetIndex >= 0 ? root.freeObjectY(freeTargetIndex)
                                                 : relayTargetIndex >= 0 ? root.relayObjectY(relayTargetIndex)
                                                 : root.height * 0.80
            readonly property bool clusterLeft: targetX >= root.centerX
            readonly property bool clusterAbove: targetY >= root.centerY
            width: 46; height: 46
            x: freeTargetIndex >= 0 ? (targetX < root.centerX ? 286 : root.width - 332)
               : relayTargetIndex >= 0 ? root.width - 332
               : targetIndex >= 0 ? (clusterLeft ? targetX - 78 : targetX + 32)
               : targetsFocusedProbe ? 33
               : 118 + (index % 4) * 170
            y: freeTargetIndex >= 0 ? Math.max(8, Math.min(root.height - 88, targetY - height / 2 + (freeTargetIndex % 2 === 0 ? -20 : 20)))
               : relayTargetIndex >= 0 ? Math.max(8, targetY - 82)
               : targetIndex >= 0 ? Math.max(8, Math.min(root.height - 88, clusterAbove ? targetY - 78 : targetY + 34))
               : targetsFocusedProbe ? root.height * 0.80 - 60
               : root.height * 0.84 + Math.floor(index / 4) * 46
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
