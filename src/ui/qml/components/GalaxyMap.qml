pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import ".."

Item {
    id: root
    property var galaxyData: ({})
    property real zoomLevel: 1.0
    property var selectedNode: null
    property string projection: "ISOMETRIC"
    signal scanRequested(int x, int y, int z)
    readonly property var nodes: galaxyData.nodes || []

    function mapX(node) {
        if (projection === "X / Y") return 1100 + Number(node.x) * 110;
        if (projection === "X / Z") return 1100 + Number(node.x) * 110;
        if (projection === "Y / Z") return 1100 + Number(node.z) * 110;
        return 1100 + (Number(node.x) - Number(node.z)) * 105;
    }
    function mapY(node) {
        if (projection === "X / Y") return 850 - Number(node.y) * 95;
        if (projection === "X / Z") return 850 - Number(node.z) * 95;
        if (projection === "Y / Z") return 850 - Number(node.y) * 95;
        return 850 + (Number(node.x) + Number(node.z) - 2 * Number(node.y)) * 52;
    }
    function depth(node) {
        if (projection === "X / Y") return Number(node.z);
        if (projection === "X / Z") return Number(node.y);
        if (projection === "Y / Z") return Number(node.x);
        return Number(node.y);
    }
    function nodeById(identifier) {
        for (let i = 0; i < nodes.length; ++i)
            if (nodes[i].id === identifier) return nodes[i];
        return null;
    }
    function fitMap() {
        zoomLevel = 1.0;
        viewport.contentX = Math.max(0, 1100 - viewport.width / 2);
        viewport.contentY = Math.max(0, 850 - viewport.height / 2);
    }

    Rectangle { anchors.fill: parent; color: Constants.voidColor; border.color: Constants.lineColor }

    Flickable {
        id: viewport
        anchors.fill: parent
        clip: true
        contentWidth: mapPlane.width * root.zoomLevel
        contentHeight: mapPlane.height * root.zoomLevel
        boundsBehavior: Flickable.StopAtBounds

        Item {
            id: scaledPlane
            width: mapPlane.width * root.zoomLevel
            height: mapPlane.height * root.zoomLevel
            Item {
                id: mapPlane
                width: 2200
                height: 1700
                scale: root.zoomLevel
                transformOrigin: Item.TopLeft

                Rectangle { x: 760; y: 850; width: 680; height: 1; color: Qt.rgba(0.1, 0.65, 0.95, 0.35) }
                Rectangle { x: 1100; y: 510; width: 1; height: 680; color: Qt.rgba(0.1, 0.95, 0.55, 0.28) }
                Label { x: 1445; y: 838; text: root.projection === "Y / Z" ? "+Z" : "+X"; color: Constants.cyanColor; font.family: Constants.technicalFont }
                Label { x: 1110; y: 500; text: root.projection === "X / Z" ? "+Z" : "+Y"; color: Constants.nominalColor; font.family: Constants.technicalFont }

                Repeater {
                    model: root.galaxyData.edges || []
                    delegate: Rectangle {
                        required property var modelData
                        property var fromNode: root.nodeById(modelData.from)
                        property var toNode: root.nodeById(modelData.to)
                        property real dx: toNode ? root.mapX(toNode) - root.mapX(fromNode) : 0
                        property real dy: toNode ? root.mapY(toNode) - root.mapY(fromNode) : 0
                        x: fromNode ? root.mapX(fromNode) : 0
                        y: fromNode ? root.mapY(fromNode) : 0
                        width: Math.sqrt(dx * dx + dy * dy)
                        height: 2
                        rotation: Math.atan2(dy, dx) * 180 / Math.PI
                        transformOrigin: Item.Left
                        color: Constants.cyanColor
                        opacity: 0.9
                    }
                }

                Repeater {
                    model: root.nodes
                    delegate: Item {
                        id: nodeItem
                        required property var modelData
                        x: root.mapX(modelData) - 15
                        y: root.mapY(modelData) - 15
                        width: 190
                        height: 48

                        Rectangle {
                            width: 30; height: 30; radius: 15
                            color: nodeItem.modelData.isFocused ? Constants.selectedColor : Constants.raisedColor
                            border.width: nodeItem.modelData.isFocused ? 3 : 1
                            border.color: nodeItem.modelData.isFocused ? Constants.nominalColor : Constants.cyanColor
                        }
                        Label {
                            x: 7; y: -15
                            text: "D" + root.depth(nodeItem.modelData)
                            color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 7
                        }
                        Label {
                            x: 38; y: 1; width: 148
                            text: nodeItem.modelData.label
                            color: nodeItem.modelData.isFocused ? Constants.nominalColor : Constants.textColor
                            font.family: Constants.technicalFont; font.pixelSize: 10; font.bold: true
                        }
                        Label {
                            x: 38; y: 18; width: 148
                            text: nodeItem.modelData.objectCount + " OBJECTS · " + nodeItem.modelData.visitCount + " VISITS"
                            color: Constants.mutedTextColor
                            font.family: Constants.technicalFont; font.pixelSize: 8
                        }
                        MouseArea {
                            anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onContainsMouseChanged: if (containsMouse) AudioManager.hover()
                            onClicked: root.selectedNode = nodeItem.modelData
                        }
                    }
                }
            }
        }

        WheelHandler {
            onWheel: event => {
                root.zoomLevel = Math.max(0.45, Math.min(2.5, root.zoomLevel * (event.angleDelta.y > 0 ? 1.12 : 0.89)));
                event.accepted = true;
            }
        }
        Component.onCompleted: root.fitMap()
    }

    Row {
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 12; spacing: 6
        ComboBox { width: 145; model: ["ISOMETRIC", "X / Y", "X / Z", "Y / Z"]; onActivated: root.projection = String(currentText) }
        Button { text: "−"; onClicked: root.zoomLevel = Math.max(0.45, root.zoomLevel - 0.15) }
        Label { width: 55; anchors.verticalCenter: parent.verticalCenter; horizontalAlignment: Text.AlignHCenter; text: Math.round(root.zoomLevel * 100) + "%"; color: Constants.textColor; font.family: Constants.technicalFont }
        Button { text: "+"; onClicked: root.zoomLevel = Math.min(2.5, root.zoomLevel + 0.15) }
        Button { text: "CENTER"; onClicked: root.fitMap() }
    }

    Label {
        anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 12
        text: root.nodes.length + " DISCOVERED SECTORS · " + (root.galaxyData.edges || []).length + " VERIFIED NEIGHBOR LINKS · FCC X/Y/Z"
        color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 9
    }

    Rectangle {
        visible: root.selectedNode !== null
        anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 12
        width: 390; height: 128; color: Constants.panelColor; border.color: Constants.cyanColor
        Column {
            anchors.fill: parent; anchors.margins: 12; spacing: 5
            Label { text: root.selectedNode ? root.selectedNode.label : ""; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
            Label { width: parent.width; text: root.selectedNode ? ((root.selectedNode.objectTypes || []).join(", ").toUpperCase() || "NO CATALOGUED OBJECTS") : ""; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 9; wrapMode: Text.Wrap }
            Label { text: root.selectedNode ? "KNOWLEDGE " + String(root.selectedNode.knowledgeLevel).toUpperCase() + " · CONFIDENCE " + Math.round(root.selectedNode.confidence * 100) + "%" : ""; color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 8 }
            Button {
                text: "SCAN / REFRESH THIS SECTOR"
                onClicked: if (root.selectedNode) root.scanRequested(root.selectedNode.x, root.selectedNode.y, root.selectedNode.z)
            }
        }
    }

    Label {
        visible: root.nodes.length === 0; anchors.centerIn: parent
        text: "NO DISCOVERED SECTORS HAVE BEEN SYNCHRONIZED YET"
        color: Constants.mutedTextColor; font.family: Constants.technicalFont
    }
}
