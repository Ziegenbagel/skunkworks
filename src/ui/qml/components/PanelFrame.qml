import QtQuick
import QtQuick.Controls
import ".."

Rectangle {
    id: root
    property string title: "PANEL"
    property alias contentItem: content.data
    color: Constants.panelColor
    border.color: Constants.lineColor
    border.width: 1
    radius: 3

    Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        Label {
            width: parent.width
            text: root.title.toUpperCase()
            color: Constants.cyanColor
            font.family: Constants.displayFont
            font.pixelSize: 13
            font.letterSpacing: 1.4
        }

        Rectangle {
            width: parent.width
            height: 1
            color: Constants.lineColor
        }

        Item {
            id: content
            width: parent.width
            height: parent.height - 42
        }
    }
}
