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
    property var selectedNode: nodes.length ? nodes[0] : null
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
    function resetCamera() {
        cameraOrigin.position = Qt.vector3d(0, 0, 0);
        cameraOrigin.eulerRotation = Qt.vector3d(-25, 35, 0);
        camera.z = 950;
    }
    function setView(rotation) {
        cameraOrigin.eulerRotation = rotation;
        camera.z = 950;
    }

    Rectangle { anchors.fill: parent; color: Constants.voidColor }

    View3D {
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
                source: "#Sphere"
                position: root.positionFor(modelData)
                scale: modelData.isFocused ? Qt.vector3d(0.34, 0.34, 0.34) : Qt.vector3d(0.24, 0.24, 0.24)
                materials: PrincipledMaterial {
                    baseColor: sectorModel.modelData.isFocused ? Constants.nominalColor : Constants.cyanColor
                    emissiveFactor: sectorModel.modelData.isFocused ? Qt.vector3d(0.1, 0.8, 0.35) : Qt.vector3d(0.05, 0.45, 0.75)
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

    Rectangle {
        anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 12
        width: 350; height: 72; color: Qt.rgba(0.03, 0.08, 0.12, 0.90); border.color: Constants.lineColor
        Column {
            anchors.fill: parent; anchors.margins: 9; spacing: 4
            Label { text: "ROTATABLE FCC GALAXY SPACE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { text: "DRAG · ORBIT    CTRL+DRAG · PAN    WHEEL · ZOOM"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9 }
            Label { text: root.nodes.length + " SECTORS · " + (root.galaxyData.edges || []).length + " VERIFIED NEIGHBOR LINKS"; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
        }
    }

    Row {
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 12; spacing: 6
        Button { text: "3D RESET"; onClicked: root.resetCamera() }
        Button { text: "TOP X/Z"; onClicked: root.setView(Qt.vector3d(-90, 0, 0)) }
        Button { text: "FRONT X/Y"; onClicked: root.setView(Qt.vector3d(0, 0, 0)) }
        Button { text: "SIDE Z/Y"; onClicked: root.setView(Qt.vector3d(0, 90, 0)) }
    }

    Rectangle {
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 12
        width: 470; height: 150; color: Qt.rgba(0.03, 0.08, 0.12, 0.94); border.color: Constants.cyanColor
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 10; spacing: 5
            ComboBox { Layout.fillWidth: true; model: root.nodes; textRole: "label"; onActivated: root.selectedNode = root.nodes[currentIndex] }
            Label { text: root.selectedNode ? root.selectedNode.label + "  ·  X " + root.selectedNode.x + "  Y " + root.selectedNode.y + "  Z " + root.selectedNode.z : "NO SECTOR SELECTED"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { Layout.fillWidth: true; text: root.selectedNode ? ((root.selectedNode.objectTypes || []).join(", ").toUpperCase() || "NO CATALOGUED OBJECTS") : ""; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9; wrapMode: Text.Wrap }
            RowLayout {
                Label { Layout.fillWidth: true; text: root.selectedNode ? "KNOWLEDGE " + String(root.selectedNode.knowledgeLevel).toUpperCase() + " · " + Math.round(root.selectedNode.confidence * 100) + "% CONFIDENCE" : ""; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
                Button { text: "SCAN / REFRESH"; enabled: root.selectedNode !== null; onClicked: if (root.selectedNode) root.scanRequested(root.selectedNode.x, root.selectedNode.y, root.selectedNode.z) }
            }
        }
    }

    Label {
        visible: root.nodes.length === 0; anchors.centerIn: parent
        text: "NO DISCOVERED SECTORS HAVE BEEN SYNCHRONIZED YET"
        color: Constants.mutedTextColor; font.family: Constants.technicalFont
    }
}
