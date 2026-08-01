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
    readonly property real spacing3D: 115
    signal scanRequested(int x, int y, int z)

    function nodeById(identifier) {
        for (let i = 0; i < nodes.length; ++i)
            if (nodes[i].id === identifier) return nodes[i];
        return null;
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
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
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
            enableXZGrid: true; enableXYGrid: true; enableYZGrid: true; enableAxisLines: true
            gridColor: Constants.lineColor; gridOpacity: 0.22
            scale: Qt.vector3d(0.12, 0.12, 0.12)
        }

        Repeater3D {
            model: root.galaxyData.edges || []
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
            model: root.nodes
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
        width: 470; height: 190; color: Qt.rgba(0.03, 0.08, 0.12, 0.94); border.color: root.selectedNode ? root.colorFor(root.selectedNode) : Constants.lineColor
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 10; spacing: 5
            ComboBox { Layout.fillWidth: true; model: root.nodes; textRole: "label"; onActivated: root.selectedNode = root.nodes[currentIndex] }
            Label { text: root.selectedNode ? root.selectedNode.label + "  ·  X " + root.selectedNode.x + "  Y " + root.selectedNode.y + "  Z " + root.selectedNode.z : "NO SECTOR SELECTED"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { Layout.fillWidth: true; text: root.selectedNode ? "STATE · " + String(root.selectedNode.mapState || "unknown").toUpperCase() + "    VISITS · " + Number(root.selectedNode.visitCount || 0) + "    OBJECTS · " + Number(root.selectedNode.objectCount || 0) : "CLICK A SECTOR DOT FOR DETAILS"; color: root.selectedNode ? root.colorFor(root.selectedNode) : Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 9; font.bold: true }
            Label { Layout.fillWidth: true; text: root.selectedNode ? ((root.selectedNode.objectTypes || []).join(", ").toUpperCase() || "NO CATALOGUED OBJECTS") : ""; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9; wrapMode: Text.Wrap }
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
    }

    Label {
        visible: root.nodes.length === 0; anchors.centerIn: parent
        text: "NO DISCOVERED SECTORS HAVE BEEN SYNCHRONIZED YET"
        color: Constants.mutedTextColor; font.family: Constants.technicalFont
    }
}
