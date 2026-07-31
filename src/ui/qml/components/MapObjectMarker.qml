pragma ComponentBehavior: Bound
import QtQuick
import ".."

Item {
    id: root

    property url iconSource
    property var badgeSources: []
    property bool selected: false
    property bool dimmed: false

    opacity: dimmed ? 0.45 : 1.0

    Image {
        anchors.fill: parent
        anchors.margins: root.selected ? parent.width * 0.10 : 0
        source: root.iconSource
        fillMode: Image.PreserveAspectFit
    }

    Image {
        visible: root.selected
        anchors.fill: parent
        source: AssetCatalog.icon("badge-selected-object")
        fillMode: Image.PreserveAspectFit
    }

    Row {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        spacing: -Math.round(root.width * 0.08)

        Repeater {
            model: root.badgeSources
            delegate: Image {
                required property string modelData
                width: root.width * 0.42
                height: width
                source: modelData
                fillMode: Image.PreserveAspectFit
            }
        }
    }
}
