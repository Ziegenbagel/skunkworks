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
    property bool hazardsOnly: false
    property bool salvageOnly: false
    property bool showRecentTrail: true
    property bool showScutCoverage: false
    property bool showAxisLabels: true
    property bool filtersExpanded: true
    property bool showDeuterium: false
    property bool showMetals: false
    property bool showIce: false
    property bool showCarbonCompounds: false
    readonly property var visibleNodes: {
        const dependency = [showCurrent, showScanned, showVisited,
                            hazardsOnly, salvageOnly, showDeuterium, showMetals,
                            showIce, showCarbonCompounds];
        return nodes.filter(function(node) { return root.matchesFilters(node); });
    }
    readonly property var visibleEdges: {
        const visible = {};
        for (let i = 0; i < visibleNodes.length; ++i) visible[visibleNodes[i].id] = true;
        return (galaxyData.edges || []).filter(function(edge) { return visible[edge.from] && visible[edge.to]; });
    }
    readonly property real spacing3D: 115
    signal scanRequested(int x, int y, int z)

    component CoverageEdge: Model {
        source: "#Cube"
        materials: DefaultMaterial {
            lighting: DefaultMaterial.NoLighting
            diffuseColor: "#176b45"
            opacity: 0.72
        }
    }

    function stateEnabled(state) {
        return (state === "current" && showCurrent)
            || (state === "scanned" && showScanned)
            || (state === "visited" && showVisited);
    }
    function matchesFilters(node) {
        if (!stateEnabled(String(node.mapState || "unknown"))) return false;
        if (hazardsOnly && !node.hasHazard) return false;
        if (salvageOnly && !node.hasDetachedContainers) return false;
        const selected = selectedResources();
        if (selected.length > 0) {
            const types = node.resourceTypes || [];
            if (!selected.some(function(resource) { return types.indexOf(resource) >= 0; }))
                return false;
        }
        return true;
    }
    function selectedResources() {
        const selected = [];
        if (showDeuterium) selected.push("deuterium");
        if (showMetals) selected.push("metals");
        if (showIce) selected.push("ice");
        if (showCarbonCompounds) selected.push("carbon_compounds");
        return selected;
    }
    function showOnlyState(state) {
        showCurrent = state === "current"; showScanned = state === "scanned";
        showVisited = state === "visited";
    }
    function showAllStates() {
        showCurrent = true; showScanned = true; showVisited = true;
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
            return "#ff9f1c";
        const selected = selectedResources();
        const matches = selected.filter(function(resource) {
            return (node.resourceTypes || []).indexOf(resource) >= 0;
        });
        if (matches.length > 0) {
            const resourceColors = {"deuterium":"#e45cff", "metals":"#ffffff", "ice":"#32c5ff", "carbon_compounds":"#34f59a"};
            // Orange is reserved for the focused probe's recent trail. A
            // multi-resource match uses its own unallocated lavender color.
            return matches.length > 1 ? "#9d7cff" : resourceColors[matches[0]];
        }
        const state = String(node.mapState || "unknown");
        if (state === "current") return "#39ff9a";
        if (state === "scanned") return "#36d9ff";
        if (state === "visited") return "#347dff";
        return "#8496a8";
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
            model: root.showScutCoverage ? (root.galaxyData.scutRanges || []) : []
            delegate: Node {
                id: coverageVolume
                required property var modelData
                readonly property real side: (Number(modelData.radius || 0) * 2 + 1) * root.spacing3D
                readonly property real halfSide: side / 2
                position: root.positionFor(modelData)

                CoverageEdge { position: Qt.vector3d(0, coverageVolume.halfSide, coverageVolume.halfSide); scale: Qt.vector3d(coverageVolume.side / 100, 0.025, 0.025) }
                CoverageEdge { position: Qt.vector3d(0, coverageVolume.halfSide, -coverageVolume.halfSide); scale: Qt.vector3d(coverageVolume.side / 100, 0.025, 0.025) }
                CoverageEdge { position: Qt.vector3d(0, -coverageVolume.halfSide, coverageVolume.halfSide); scale: Qt.vector3d(coverageVolume.side / 100, 0.025, 0.025) }
                CoverageEdge { position: Qt.vector3d(0, -coverageVolume.halfSide, -coverageVolume.halfSide); scale: Qt.vector3d(coverageVolume.side / 100, 0.025, 0.025) }
                CoverageEdge { position: Qt.vector3d(coverageVolume.halfSide, 0, coverageVolume.halfSide); scale: Qt.vector3d(0.025, coverageVolume.side / 100, 0.025) }
                CoverageEdge { position: Qt.vector3d(coverageVolume.halfSide, 0, -coverageVolume.halfSide); scale: Qt.vector3d(0.025, coverageVolume.side / 100, 0.025) }
                CoverageEdge { position: Qt.vector3d(-coverageVolume.halfSide, 0, coverageVolume.halfSide); scale: Qt.vector3d(0.025, coverageVolume.side / 100, 0.025) }
                CoverageEdge { position: Qt.vector3d(-coverageVolume.halfSide, 0, -coverageVolume.halfSide); scale: Qt.vector3d(0.025, coverageVolume.side / 100, 0.025) }
                CoverageEdge { position: Qt.vector3d(coverageVolume.halfSide, coverageVolume.halfSide, 0); scale: Qt.vector3d(0.025, 0.025, coverageVolume.side / 100) }
                CoverageEdge { position: Qt.vector3d(coverageVolume.halfSide, -coverageVolume.halfSide, 0); scale: Qt.vector3d(0.025, 0.025, coverageVolume.side / 100) }
                CoverageEdge { position: Qt.vector3d(-coverageVolume.halfSide, coverageVolume.halfSide, 0); scale: Qt.vector3d(0.025, 0.025, coverageVolume.side / 100) }
                CoverageEdge { position: Qt.vector3d(-coverageVolume.halfSide, -coverageVolume.halfSide, 0); scale: Qt.vector3d(0.025, 0.025, coverageVolume.side / 100) }
            }
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
                materials: DefaultMaterial {
                    lighting: DefaultMaterial.NoLighting
                    diffuseColor: root.colorFor(sectorModel.modelData)
                }
            }
        }
    }

    OrbitCameraController {
        anchors.fill: parent
        origin: cameraOrigin; camera: camera; panEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
    }

    // Project the FCC origin and positive axis markers over the 3D scene so
    // their labels remain readable while the user orbits, pans, and zooms.
    Repeater {
        visible: root.showAxisLabels
        model: [
            { "label": "X", "x": 1.15, "y": 0, "z": 0, "color": "#ff5d68" },
            { "label": "Y", "x": 0, "y": 1.15, "z": 0, "color": "#39ff9a" },
            { "label": "Z", "x": 0, "y": 0, "z": 1.15, "color": "#4f8cff" }
        ]
        delegate: Rectangle {
            id: axisMarker
            required property var modelData
            readonly property vector3d projected: {
                // Explicit camera dependencies keep mapFrom3DScene current.
                const orbit = cameraOrigin.eulerRotation;
                const center = cameraOrigin.position;
                const zoom = camera.z;
                return galaxyView.mapFrom3DScene(Qt.vector3d(
                    Number(modelData.x) * root.spacing3D,
                    Number(modelData.y) * root.spacing3D,
                    Number(modelData.z) * root.spacing3D
                ));
            }
            x: projected.x - width / 2
            y: projected.y - height / 2
            width: axisMarkerLabel.implicitWidth + 12
            height: axisMarkerLabel.implicitHeight + 6
            radius: 2
            color: Qt.rgba(0.01, 0.04, 0.06, 0.86)
            border.color: modelData.color
            z: 2

            Label {
                id: axisMarkerLabel
                anchors.centerIn: parent
                text: axisMarker.modelData.label
                color: axisMarker.modelData.color
                font.family: Constants.technicalFont
                font.pixelSize: 14
                font.bold: true
            }
        }
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
        width: 500; height: 90; color: Qt.rgba(0.03, 0.08, 0.12, 0.90); border.color: Constants.lineColor
        Column {
            anchors.fill: parent; anchors.margins: 9; spacing: 4
            Label { text: "ROTATABLE FCC GALAXY SPACE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { text: "LEFT DRAG · ORBIT    RIGHT/MIDDLE DRAG · PAN    WHEEL · ZOOM"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 12 }
            Label { text: root.nodes.length + " SECTORS · " + (root.galaxyData.edges || []).length + " VERIFIED NEIGHBOR LINKS"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 12 }
        }
    }

    Rectangle {
        anchors.left: parent.left; anchors.top: parent.top
        anchors.leftMargin: 12; anchors.topMargin: 384
        width: 560; height: root.filtersExpanded ? 490 : 48
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
                    color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 12
                }
                Button {
                    text: root.filtersExpanded ? "▲" : "▼"
                    Accessible.name: root.filtersExpanded ? "Collapse map filters" : "Expand map filters"
                    onClicked: root.filtersExpanded = !root.filtersExpanded
                }
            }
            Label { visible: root.filtersExpanded; text: "DISCOVERY STATE"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 12 }
            GridLayout {
                visible: root.filtersExpanded; Layout.fillWidth: true
                columns: 3; columnSpacing: 4; rowSpacing: 2
                CheckBox { text: "CURRENT"; checked: root.showCurrent; onToggled: root.showCurrent = checked }
                CheckBox { text: "SCANNED"; checked: root.showScanned; onToggled: root.showScanned = checked }
                CheckBox { text: "VISITED"; checked: root.showVisited; onToggled: root.showVisited = checked }
                Button { text: "SHOW ALL"; onClicked: root.showAllStates() }
            }
            RowLayout {
                visible: root.filtersExpanded; Layout.fillWidth: true
                Button { text: "ONLY VISITED"; onClicked: root.showOnlyState("visited") }
                Button { text: "ONLY SCANNED"; onClicked: root.showOnlyState("scanned") }
            }
            Label { visible: root.filtersExpanded; text: "HAS ANY SELECTED RESOURCE"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 12 }
            GridLayout {
                visible: root.filtersExpanded; Layout.fillWidth: true
                columns: 2; columnSpacing: 5; rowSpacing: 2
                CheckBox { text: "DEUTERIUM"; checked: root.showDeuterium; onToggled: root.showDeuterium = checked }
                CheckBox { text: "METALS"; checked: root.showMetals; onToggled: root.showMetals = checked }
                CheckBox { text: "ICE"; checked: root.showIce; onToggled: root.showIce = checked }
                CheckBox { text: "ORGANIC / CARBON COMPOUNDS"; checked: root.showCarbonCompounds; onToggled: root.showCarbonCompounds = checked }
                Label {
                    Layout.columnSpan: 2; Layout.fillWidth: true
                    text: "MULTIPLE SELECTED RESOURCES · LAVENDER"
                    color: "#9d7cff"; font.family: Constants.technicalFont; font.pixelSize: 12
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
                CheckBox {
                    Layout.columnSpan: 2
                    text: "SHOW FULL SCUT COVERAGE VOLUMES"
                    checked: root.showScutCoverage; onToggled: root.showScutCoverage = checked
                }
                CheckBox {
                    Layout.columnSpan: 2
                    text: "SHOW X / Y / Z AXIS LABELS"
                    checked: root.showAxisLabels; onToggled: root.showAxisLabels = checked
                }
            }
            Label {
                visible: root.filtersExpanded; Layout.fillWidth: true
                text: root.visibleNodes.length + " OF " + root.nodes.length + " SECTORS VISIBLE · "
                    + Number(root.galaxyData.recentTrailCount || 0) + " RECENT ROUTE SEGMENTS"
                color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 12
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
        width: 520; height: 280; color: Qt.rgba(0.03, 0.08, 0.12, 0.94); border.color: root.selectedNode ? root.colorFor(root.selectedNode) : Constants.lineColor
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 10; spacing: 5
            ComboBox { Layout.fillWidth: true; model: root.visibleNodes; textRole: "label"; onActivated: root.selectedNode = root.visibleNodes[currentIndex] }
            Label { text: root.selectedNode ? root.selectedNode.label + "  ·  X " + root.selectedNode.x + "  Y " + root.selectedNode.y + "  Z " + root.selectedNode.z : "NO SECTOR SELECTED"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { Layout.fillWidth: true; text: root.selectedNode ? "STATE · " + String(root.selectedNode.mapState || "unknown").toUpperCase() + "    VISITS · " + Number(root.selectedNode.visitCount || 0) + "    OBJECTS · " + Number(root.selectedNode.objectCount || 0) : "CLICK A SECTOR DOT FOR DETAILS"; color: root.selectedNode ? root.colorFor(root.selectedNode) : Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 12; font.bold: true }
            Label { Layout.fillWidth: true; text: root.selectedNode ? ((root.selectedNode.objectTypes || []).join(", ").toUpperCase() || "NO CATALOGUED OBJECTS") : ""; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 12; wrapMode: Text.Wrap }
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
                            Label { anchors.verticalCenter: parent.verticalCenter; text: (objectDetail.modelData.estimated ? "EST. " : "") + String(objectDetail.modelData.name || objectDetail.modelData.type).toUpperCase(); color: objectDetail.modelData.estimated ? Constants.warningColor : Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 12 }
                        }
                    }
                }
            }
            Label { Layout.fillWidth: true; text: root.selectedNode ? "OBSERVED BY PROBES · " + ((root.selectedNode.probeIds || []).join(", ") || "NONE") + (root.selectedNode.lastVisitedAt ? "    LAST VISIT · " + root.selectedNode.lastVisitedAt : "") : ""; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 12; wrapMode: Text.Wrap }
            RowLayout {
                Label { Layout.fillWidth: true; text: root.selectedNode ? "KNOWLEDGE " + String(root.selectedNode.knowledgeLevel).toUpperCase() + " · " + Math.round(root.selectedNode.confidence * 100) + "% CONFIDENCE" : ""; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 12 }
                Button { text: "SCAN / REFRESH"; enabled: root.selectedNode !== null; onClicked: if (root.selectedNode) root.scanRequested(root.selectedNode.x, root.selectedNode.y, root.selectedNode.z) }
            }
        }
    }

    Row {
        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 12
        spacing: 18
        Repeater {
            model: [{"label":"CURRENT", "color":Constants.nominalColor}, {"label":"SCANNED", "color":Constants.cyanColor}, {"label":"VISITED", "color":"#0e6cff"}, {"label":"DEUTERIUM", "color":"#e45cff"}, {"label":"METALS", "color":"#ffffff"}, {"label":"ICE", "color":"#32c5ff"}, {"label":"CARBON", "color":"#34f59a"}, {"label":"MULTIPLE", "color":"#9d7cff"}]
            delegate: Row {
                required property var modelData; spacing: 8
                Rectangle { width: 18; height: 18; radius: 9; color: parent.modelData.color }
                Label { text: parent.modelData.label; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 14 }
            }
        }
        Row {
            spacing: 8
            Rectangle { width: 30; height: 7; anchors.verticalCenter: parent.verticalCenter; color: Constants.warningColor }
            Label { text: "RECENT TRAIL"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 14 }
            Rectangle { width: 30; height: 4; anchors.verticalCenter: parent.verticalCenter; color: "#176b45" }
            Label { text: "SCUT COVERAGE"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 14 }
        }
    }

    Label {
        visible: root.nodes.length === 0; anchors.centerIn: parent
        text: "NO DISCOVERED SECTORS HAVE BEEN SYNCHRONIZED YET"
        color: Constants.mutedTextColor; font.family: Constants.technicalFont
    }
}
