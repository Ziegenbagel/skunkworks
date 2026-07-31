import QtQuick
import ".."

Item {
    id: root

    // Normalized positions let the same overlay serve sector and galaxy maps.
    property var nodes: [
        {
            "x": 0.18,
            "y": 0.70,
            "beacon": true
        },
        {
            "x": 0.46,
            "y": 0.30,
            "beacon": true
        },
        {
            "x": 0.78,
            "y": 0.56,
            "beacon": true
        }
    ]
    property var edges: [[0, 1], [1, 2]]
    property color routeColor: Constants.cyanColor

    Canvas {
        id: routes
        anchors.fill: parent

        onPaint: {
            const context = getContext("2d");
            context.reset();
            if (!root.nodes || root.nodes.length < 2)
                return;
            function drawRoutes(width, color, dash) {
                context.lineWidth = width;
                context.strokeStyle = color;
                context.setLineDash(dash);
                for (let index = 0; index < root.edges.length; ++index) {
                    const edge = root.edges[index];
                    const origin = root.nodes[edge[0]];
                    const destination = root.nodes[edge[1]];
                    if (!origin || !destination || !origin.beacon || !destination.beacon)
                        continue;
                    context.beginPath();
                    context.moveTo(origin.x * routes.width, origin.y * routes.height);
                    context.lineTo(destination.x * routes.width, destination.y * routes.height);
                    context.stroke();
                }
            }

            drawRoutes(7, "#071017", []);
            drawRoutes(3, root.routeColor, [10, 7]);
        }

        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    Repeater {
        model: root.nodes
        delegate: Item {
            required property var modelData
            x: modelData.x * root.width - width / 2
            y: modelData.y * root.height - height / 2
            width: Math.max(28, Math.min(root.width, root.height) * 0.095)
            height: width

            Image {
                anchors.fill: parent
                source: AssetCatalog.icon("scut-relay")
                fillMode: Image.PreserveAspectFit
            }

            Image {
                visible: modelData.beacon
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                width: parent.width * 0.48
                height: width
                source: AssetCatalog.icon("badge-scut-transit-beacon")
                fillMode: Image.PreserveAspectFit
            }
        }
    }
}
