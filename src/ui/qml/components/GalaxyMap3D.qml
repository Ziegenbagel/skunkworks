pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick3D
import QtQuick3D.Helpers
import ".."

Item {
    id: root
    property var galaxyData: ({})
    property int focusedProbeId: -1
    property var selectedNode: null
    readonly property var nodes: galaxyData.nodes || []
    readonly property var nodeIndex: {
        const result = {};
        for (let i = 0; i < nodes.length; ++i)
            result[String(nodes[i].id)] = nodes[i];
        return result;
    }
    readonly property var recentTrailNodes: {
        const result = {};
        const nodeIds = galaxyData.recentTrailNodes || [];
        for (let i = 0; i < nodeIds.length; ++i)
            result[String(nodeIds[i])] = true;
        const trail = galaxyData.recentTrail || [];
        for (let i = 0; i < trail.length; ++i) {
            result[String(trail[i].from)] = true;
            result[String(trail[i].to)] = true;
        }
        return result;
    }
    property bool showCurrent: true
    property bool showScanned: true
    property bool showVisited: true
    property bool showObserved: true
    property bool showUnknown: true
    property bool hazardsOnly: false
    property bool salvageOnly: false
    property bool showRecentTrail: true
    property bool filtersExpanded: true
    property string resourceFilter: "all"
    property string resourceMode: "all"
    readonly property var visibleNodes: {
        const dependency = [showCurrent, showScanned, showVisited, showObserved, showUnknown,
                            hazardsOnly, salvageOnly, resourceFilter, resourceMode];
        return nodes.filter(function(node) { return root.matchesFilters(node); });
    }
    readonly property var visibleEdges: {
        const visible = {};
        for (let i = 0; i < visibleNodes.length; ++i) visible[visibleNodes[i].id] = true;
        return (galaxyData.edges || []).filter(function(edge) { return visible[edge.from] && visible[edge.to]; });
    }
    readonly property real spacing3D: 115
    signal scanRequested(int x, int y, int z)

    function stateEnabled(state) {
        return (state === "current" && showCurrent) || (state === "scanned" && showScanned)
            || (state === "visited" && showVisited) || (state === "observed" && showObserved)
            || (state === "unknown" && showUnknown);
    }
    function matchesFilters(node) {
        if (!stateEnabled(String(node.mapState || "unknown"))) return false;
        if (hazardsOnly && !node.hasHazard) return false;
        if (salvageOnly && !node.hasDetachedContainers) return false;
        if (resourceMode !== "all" && resourceFilter !== "all") {
            const types = node.resourceTypes || [];
            const hasResource = types.indexOf(resourceFilter) >= 0;
            if (resourceMode === "has" && !hasResource) return false;
            // Absence is authoritative only after a sector has been scanned.
            if (resourceMode === "without"
                    && (String(node.knowledgeLevel || "unknown") === "unknown" || hasResource)) return false;
        }
        return true;
    }
    function showOnlyState(state) {
        showCurrent = state === "current"; showScanned = state === "scanned";
        showVisited = state === "visited"; showObserved = state === "observed";
        showUnknown = state === "unknown";
    }
    function showAllStates() {
        showCurrent = true; showScanned = true; showVisited = true;
        showObserved = true; showUnknown = true;
    }

    function nodeById(identifier) {
        return nodeIndex[String(identifier)] || null;
    }
    function positionFor(node) {
        return Qt.vector3d(Number(node.x) * spacing3D, Number(node.y) * spacing3D, Number(node.z) * spacing3D);
    }
    function focusedNode() {
        for (let i = 0; i < nodes.length; ++i) {
            if (nodes[i].isFocused) return nodes[i];
            const probeIds = nodes[i].probeIds || [];
            if (probeIds.indexOf(focusedProbeId) >= 0 || probeIds.indexOf(String(focusedProbeId)) >= 0)
                return nodes[i];
        }
        return null;
    }
    function centerOnFocusedProbe() {
        const target = focusedNode();
        cameraOrigin.position = target ? positionFor(target) : Qt.vector3d(0, 0, 0);
        if (target) selectedNode = target;
    }
    function resetCamera() {
        centerOnFocusedProbe();
        cameraOrigin.eulerRotation = Qt.vector3d(-25, 35, 0);
        camera.z = 950;
    }
    function setView(rotation) {
        cameraOrigin.eulerRotation = rotation;
        camera.z = 950;
    }
    function panBy(horizontal, vertical) {
        const step = Math.max(30, camera.z * 0.08);
        cameraOrigin.position = Qt.vector3d(
            cameraOrigin.position.x + horizontal * step,
            cameraOrigin.position.y + vertical * step,
            cameraOrigin.position.z
        );
    }
    function colorFor(node) {
        if (showRecentTrail && recentTrailNodes[String(node.id)])
            return Constants.warningColor;
        if (resourceMode === "has" && resourceFilter !== "all"
                && (node.resourceTypes || []).indexOf(resourceFilter) >= 0) {
            const resourceColors = {"deuterium":"#c76dff", "metals":"#d7dce5", "ice":"#69bfff", "carbon_compounds":"#69d391"};
            return resourceColors[resourceFilter] || Constants.cyanColor;
        }
        const state = String(node.mapState || "unknown");
        if (state === "current") return Constants.nominalColor;
        if (state === "scanned") return Constants.cyanColor;
        if (state === "visited") return "#0e6cff";
        if (state === "observed") return Constants.warningColor;
        return "#657384";
    }

    Rectangle { anchors.fill: parent; color: Constants.voidColor }

    View3D {
        id: galaxyView
        anchors.fill: parent
        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Color
            clearColor: Constants.voidColor
            // MSAA made orbit/pan noticeably jittery once a modest route was
            // discovered. Geometry is already large enough to remain legible.
            antialiasingMode: SceneEnvironment.NoAA
        }

        Node {
            id: cameraOrigin
            eulerRotation: Qt.vector3d(-25, 35, 0)
            PerspectiveCamera { id: camera; z: 950; fieldOfView: 45 }
        }
        camera: camera

        DirectionalLight { eulerRotation: Qt.vector3d(-35, -35, 0); brightness: 1.3 }
        DirectionalLight { eulerRotation: Qt.vector3d(35, 145, 0); brightness: 0.55; color: Constants.cyanColor }
        AxisHelper {
            enableXZGrid: false; enableXYGrid: false; enableYZGrid: false; enableAxisLines: true
            gridColor: Constants.lineColor; gridOpacity: 0.22
            scale: Qt.vector3d(0.12, 0.12, 0.12)
        }

        Repeater3D {
            model: root.visibleEdges
            delegate: Model {
                id: linkModel
                required property var modelData
                property var fromNode: root.nodeById(modelData.from)
                property var toNode: root.nodeById(modelData.to)
                property vector3d fromPosition: fromNode ? root.positionFor(fromNode) : Qt.vector3d(0, 0, 0)
                property vector3d toPosition: toNode ? root.positionFor(toNode) : Qt.vector3d(0, 0, 0)
                property real dx: toPosition.x - fromPosition.x
                property real dy: toPosition.y - fromPosition.y
                property real dz: toPosition.z - fromPosition.z
                property real linkLength: Math.sqrt(dx * dx + dy * dy + dz * dz)
                source: "#Cube"
                position: Qt.vector3d((fromPosition.x + toPosition.x) / 2, (fromPosition.y + toPosition.y) / 2, (fromPosition.z + toPosition.z) / 2)
                scale: Qt.vector3d(linkLength / 100, 0.018, 0.018)
                eulerRotation: Qt.vector3d(0, -Math.atan2(dz, dx) * 180 / Math.PI, Math.atan2(dy, Math.sqrt(dx * dx + dz * dz)) * 180 / Math.PI)
                materials: DefaultMaterial { lighting: DefaultMaterial.NoLighting; diffuseColor: Constants.cyanColor; opacity: 0.82 }
            }
        }

        Repeater3D {
            model: root.showRecentTrail ? (root.galaxyData.recentTrail || []) : []
            delegate: Model {
                id: trailModel
                required property var modelData
                property var fromNode: root.nodeById(modelData.from)
                property var toNode: root.nodeById(modelData.to)
                property vector3d fromPosition: fromNode ? root.positionFor(fromNode) : Qt.vector3d(0, 0, 0)
                property vector3d toPosition: toNode ? root.positionFor(toNode) : Qt.vector3d(0, 0, 0)
                property real dx: toPosition.x - fromPosition.x
                property real dy: toPosition.y - fromPosition.y
                property real dz: toPosition.z - fromPosition.z
                property real linkLength: Math.sqrt(dx * dx + dy * dy + dz * dz)
                visible: fromNode !== null && toNode !== null
                source: "#Cube"
                position: Qt.vector3d((fromPosition.x + toPosition.x) / 2, (fromPosition.y + toPosition.y) / 2, (fromPosition.z + toPosition.z) / 2)
                scale: Qt.vector3d(linkLength / 100, 0.045, 0.045)
                eulerRotation: Qt.vector3d(0, -Math.atan2(dz, dx) * 180 / Math.PI, Math.atan2(dy, Math.sqrt(dx * dx + dz * dz)) * 180 / Math.PI)
                materials: DefaultMaterial { lighting: DefaultMaterial.NoLighting; diffuseColor: Constants.warningColor; opacity: 0.96 }
            }
        }

        Repeater3D {
            model: root.visibleNodes
            delegate: Model {
                id: sectorModel
                required property var modelData
                objectName: String(modelData.id)
                source: "#Sphere"
                pickable: true
                position: root.positionFor(modelData)
                scale: modelData.isFocused ? Qt.vector3d(0.34, 0.34, 0.34) : Qt.vector3d(0.24, 0.24, 0.24)
                materials: PrincipledMaterial {
                    baseColor: root.colorFor(sectorModel.modelData)
                    emissiveFactor: sectorModel.modelData.isFocused ? Qt.vector3d(0.1, 0.8, 0.35) : Qt.vector3d(0.04, 0.30, 0.46)
                    roughness: 0.28; metalness: 0.35
                }
            }
        }
    }

    OrbitCameraController {
        anchors.fill: parent
        origin: cameraOrigin; camera: camera; panEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
    }

    Component.onCompleted: Qt.callLater(root.resetCamera)
    onGalaxyDataChanged: Qt.callLater(root.resetCamera)
    onFocusedProbeIdChanged: Qt.callLater(root.resetCamera)

    TapHandler {
        acceptedButtons: Qt.LeftButton
        gesturePolicy: TapHandler.ReleaseWithinBounds
        onTapped: (eventPoint, button) => {
            const hit = galaxyView.pick(eventPoint.position.x, eventPoint.position.y);
            if (hit.objectHit)
                root.selectedNode = root.nodeById(String(hit.objectHit.objectName));
        }
    }

    Rectangle {
        anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 12
        width: 350; height: 72; color: Qt.rgba(0.03, 0.08, 0.12, 0.90); border.color: Constants.lineColor
        Column {
            anchors.fill: parent; anchors.margins: 9; spacing: 4
            Label { text: "ROTATABLE FCC GALAXY SPACE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { text: "LEFT DRAG · ORBIT    RIGHT/MIDDLE DRAG · PAN    WHEEL · ZOOM"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
            Label { text: root.nodes.length + " SECTORS · " + (root.galaxyData.edges || []).length + " VERIFIED NEIGHBOR LINKS"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
        }
    }

    Rectangle {
        anchors.left: parent.left; anchors.top: parent.top
        anchors.leftMargin: 12; anchors.topMargin: 354
        width: 470; height: root.filtersExpanded ? 330 : 42
        color: Qt.rgba(0.03, 0.08, 0.12, 0.94); border.color: Constants.lineColor
        clip: true
        Behavior on height { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 10; spacing: 5
            RowLayout {
                Layout.fillWidth: true
                Label { text: "MAP FILTERS"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                Item { Layout.fillWidth: true }
                Label {
                    visible: !root.filtersExpanded
                    text: root.visibleNodes.length + " / " + root.nodes.length + " VISIBLE"
                    color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 9
                }
                Button {
                    text: root.filtersExpanded ? "▲" : "▼"
                    Accessible.name: root.filtersExpanded ? "Collapse map filters" : "Expand map filters"
                    onClicked: root.filtersExpanded = !root.filtersExpanded
                }
            }
            Label { visible: root.filtersExpanded; text: "DISCOVERY STATE"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
            GridLayout {
                visible: root.filtersExpanded; Layout.fillWidth: true
                columns: 3; columnSpacing: 4; rowSpacing: 2
                CheckBox { text: "CURRENT"; checked: root.showCurrent; onToggled: root.showCurrent = checked }
                CheckBox { text: "SCANNED"; checked: root.showScanned; onToggled: root.showScanned = checked }
                CheckBox { text: "VISITED"; checked: root.showVisited; onToggled: root.showVisited = checked }
                CheckBox { text: "OBSERVED"; checked: root.showObserved; onToggled: root.showObserved = checked }
                CheckBox { text: "UNKNOWN"; checked: root.showUnknown; onToggled: root.showUnknown = checked }
                Button { text: "SHOW ALL"; onClicked: root.showAllStates() }
            }
            RowLayout {
                visible: root.filtersExpanded; Layout.fillWidth: true
                Button { text: "ONLY UNEXPLORED"; onClicked: root.showOnlyState("unknown") }
                Button { text: "ONLY VISITED"; onClicked: root.showOnlyState("visited") }
                Button { text: "ONLY SCANNED"; onClicked: root.showOnlyState("scanned") }
            }
            RowLayout {
                visible: root.filtersExpanded; Layout.fillWidth: true
                ComboBox {
                    id: resourceModeBox; Layout.preferredWidth: 170
                    model: [{text:"ALL SYSTEMS", value:"all"}, {text:"HAS RESOURCE", value:"has"}, {text:"CONFIRMED WITHOUT", value:"without"}]
                    textRole: "text"; valueRole: "value"; onActivated: root.resourceMode = currentValue
                }
                ComboBox {
                    id: resourceTypeBox; Layout.fillWidth: true
                    model: [{text:"ANY RESOURCE", value:"all"}, {text:"DEUTERIUM", value:"deuterium"}, {text:"METALS", value:"metals"}, {text:"ICE", value:"ice"}, {text:"ORGANIC / CARBON COMPOUNDS", value:"carbon_compounds"}]
                    textRole: "text"; valueRole: "value"; onActivated: root.resourceFilter = currentValue
                }
            }
            GridLayout {
                visible: root.filtersExpanded; Layout.fillWidth: true
                columns: 2; columnSpacing: 5; rowSpacing: 2
                CheckBox { text: "HAZARDS ONLY"; checked: root.hazardsOnly; onToggled: root.hazardsOnly = checked }
                CheckBox { text: "DROPPED CONTAINERS"; checked: root.salvageOnly; onToggled: root.salvageOnly = checked }
                CheckBox {
                    Layout.columnSpan: 2
                    text: "FOCUSED PROBE · RECENT 10 TRAIL"
                    checked: root.showRecentTrail; onToggled: root.showRecentTrail = checked
                }
            }
            Label {
                visible: root.filtersExpanded; Layout.fillWidth: true
                text: root.visibleNodes.length + " OF " + root.nodes.length + " SECTORS VISIBLE · "
                    + Number(root.galaxyData.recentTrailCount || 0) + " RECENT ROUTE SEGMENTS"
                color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 9
            }
        }
    }

    Column {
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 12; spacing: 6
        Row {
            spacing: 6
            Button { text: "CENTER PROBE"; onClicked: root.resetCamera() }
            Button { text: "TOP X/Z"; onClicked: root.setView(Qt.vector3d(-90, 0, 0)) }
            Button { text: "FRONT X/Y"; onClicked: root.setView(Qt.vector3d(0, 0, 0)) }
            Button { text: "SIDE Z/Y"; onClicked: root.setView(Qt.vector3d(0, 90, 0)) }
        }
        Row {
            anchors.right: parent.right; spacing: 6
            Label { text: "PAN"; anchors.verticalCenter: parent.verticalCenter; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
            Button { text: "◀"; onClicked: root.panBy(-1, 0) }
            Button { text: "▲"; onClicked: root.panBy(0, 1) }
            Button { text: "▼"; onClicked: root.panBy(0, -1) }
            Button { text: "▶"; onClicked: root.panBy(1, 0) }
        }
    }

    Rectangle {
        anchors.left: parent.left; anchors.top: parent.top; anchors.leftMargin: 12; anchors.topMargin: 94
        width: 470; height: 250; color: Qt.rgba(0.03, 0.08, 0.12, 0.94); border.color: root.selectedNode ? root.colorFor(root.selectedNode) : Constants.lineColor
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 10; spacing: 5
            ComboBox { Layout.fillWidth: true; model: root.visibleNodes; textRole: "label"; onActivated: root.selectedNode = root.visibleNodes[currentIndex] }
            Label { text: root.selectedNode ? root.selectedNode.label + "  ·  X " + root.selectedNode.x + "  Y " + root.selectedNode.y + "  Z " + root.selectedNode.z : "NO SECTOR SELECTED"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { Layout.fillWidth: true; text: root.selectedNode ? "STATE · " + String(root.selectedNode.mapState || "unknown").toUpperCase() + "    VISITS · " + Number(root.selectedNode.visitCount || 0) + "    OBJECTS · " + Number(root.selectedNode.objectCount || 0) : "CLICK A SECTOR DOT FOR DETAILS"; color: root.selectedNode ? root.colorFor(root.selectedNode) : Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 9; font.bold: true }
            Label { Layout.fillWidth: true; text: root.selectedNode ? ((root.selectedNode.objectTypes || []).join(", ").toUpperCase() || "NO CATALOGUED OBJECTS") : ""; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9; wrapMode: Text.Wrap }
            ScrollView {
                visible: root.selectedNode && (root.selectedNode.objects || []).length > 0
                Layout.fillWidth: true; Layout.preferredHeight: 62; clip: true
                Row {
                    spacing: 10
                    Repeater {
                        model: root.selectedNode ? (root.selectedNode.objects || []) : []
                        delegate: Row {
                            id: objectDetail
                            required property var modelData; spacing: 4
                            Image { width: 28; height: 28; source: objectDetail.modelData.estimated ? AssetCatalog.icon("unknown-object") : AssetCatalog.objectIcon(objectDetail.modelData.type, objectDetail.modelData); fillMode: Image.PreserveAspectFit }
                            Label { anchors.verticalCenter: parent.verticalCenter; text: (objectDetail.modelData.estimated ? "EST. " : "") + String(objectDetail.modelData.name || objectDetail.modelData.type).toUpperCase(); color: objectDetail.modelData.estimated ? Constants.warningColor : Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
                        }
                    }
                }
            }
            Label { Layout.fillWidth: true; text: root.selectedNode ? "OBSERVED BY PROBES · " + ((root.selectedNode.probeIds || []).join(", ") || "NONE") + (root.selectedNode.lastVisitedAt ? "    LAST VISIT · " + root.selectedNode.lastVisitedAt : "") : ""; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8; wrapMode: Text.Wrap }
            RowLayout {
                Label { Layout.fillWidth: true; text: root.selectedNode ? "KNOWLEDGE " + String(root.selectedNode.knowledgeLevel).toUpperCase() + " · " + Math.round(root.selectedNode.confidence * 100) + "% CONFIDENCE" : ""; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
                Button { text: "SCAN / REFRESH"; enabled: root.selectedNode !== null; onClicked: if (root.selectedNode) root.scanRequested(root.selectedNode.x, root.selectedNode.y, root.selectedNode.z) }
            }
        }
    }

    Row {
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 12; spacing: 14
        Repeater {
            model: [{"label":"CURRENT", "color":Constants.nominalColor}, {"label":"SCANNED", "color":Constants.cyanColor}, {"label":"VISITED", "color":"#0e6cff"}, {"label":"OBSERVED", "color":Constants.warningColor}, {"label":"UNKNOWN", "color":"#657384"}]
            delegate: Row {
                required property var modelData; spacing: 5
                Rectangle { width: 10; height: 10; radius: 5; color: parent.modelData.color }
                Label { text: parent.modelData.label; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
            }
        }
        Row {
            spacing: 5
            Rectangle { width: 18; height: 4; anchors.verticalCenter: parent.verticalCenter; color: Constants.warningColor }
            Label { text: "FOCUSED PROBE RECENT TRAIL"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
        }
    }

    Label {
        visible: root.nodes.length === 0; anchors.centerIn: parent
        text: "NO DISCOVERED SECTORS HAVE BEEN SYNCHRONIZED YET"
        color: Constants.mutedTextColor; font.family: Constants.technicalFont
    }
}
