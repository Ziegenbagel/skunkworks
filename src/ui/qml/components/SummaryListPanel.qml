pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import ".."

PanelFrame {
    id: root

    property var entries: []
    property string emptyText: "No active items"
    property string detailTitle: title
    property int previewLimit: 3

    contentItem: Item {
        anchors.fill: parent

        Column {
            anchors.fill: parent
            spacing: 9

            Repeater {
                model: root.entries.length ? root.entries : [
                    {
                        "displayText": root.emptyText,
                        "detailText": root.emptyText
                    }
                ]
                delegate: Label {
                    required property var modelData
                    required property int index
                    visible: index < root.previewLimit
                    width: parent.width
                    text: modelData.displayText
                    color: root.entries.length ? Constants.textColor : Constants.mutedTextColor
                    elide: Text.ElideRight
                    font.family: Constants.technicalFont
                    font.pixelSize: 9
                }
            }

            Item {
                width: 1
                height: 2
            }

            Label {
                text: root.entries.length + (root.entries.length === 1 ? " ACTIVE ITEM" : " ACTIVE ITEMS") + "  ·  CLICK FOR FULL DETAILS ›"
                color: Constants.cyanColor
                font.family: Constants.technicalFont
                font.pixelSize: 8
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: details.open()
        }
    }

    Dialog {
        id: details
        objectName: root.objectName + "Dialog"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(920, parent.width * 0.72)
        height: Math.min(680, parent.height * 0.78)
        modal: true
        title: root.detailTitle

        header: Rectangle {
            implicitHeight: 48
            color: Constants.raisedColor
            border.color: Constants.lineColor

            Label {
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                anchors.leftMargin: 16
                text: root.detailTitle.toUpperCase()
                color: Constants.cyanColor
                font.family: Constants.displayFont
                font.pixelSize: 13
                font.bold: true
                font.letterSpacing: 1.2
            }
        }

        footer: Rectangle {
            implicitHeight: 54
            color: Constants.panelColor
            border.color: Constants.lineColor

            Button {
                id: closeButton
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 14
                width: 110
                height: 32
                text: "CLOSE"
                onClicked: details.close()

                background: Rectangle {
                    color: Constants.raisedColor
                    border.color: Constants.cyanColor
                    radius: 2
                }

                contentItem: Label {
                    text: closeButton.text
                    color: Constants.textColor
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    font.family: Constants.technicalFont
                    font.pixelSize: 10
                }
            }
        }

        background: Rectangle {
            color: Constants.panelColor
            border.color: Constants.cyanColor
            border.width: 1
            radius: 3
        }

        contentItem: Rectangle {
            color: Constants.voidColor
            border.color: Constants.lineColor

            ScrollView {
                anchors.fill: parent
                anchors.margins: 12
                clip: true

                ListView {
                    id: detailList
                    model: root.entries.length ? root.entries : [
                        {
                            "displayText": root.emptyText,
                            "detailText": root.emptyText
                        }
                    ]
                    spacing: 8

                    delegate: Rectangle {
                        id: detailRow
                        required property var modelData
                        required property int index
                        width: detailList.width
                        height: detailColumn.implicitHeight + 24
                        color: index % 2 ? Constants.panelColor : Constants.raisedColor
                        border.color: Constants.lineColor
                        radius: 2

                        Column {
                            id: detailColumn
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 12
                            spacing: 7

                            Label {
                                width: parent.width
                                text: detailRow.modelData.displayText
                                color: Constants.cyanColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 11
                                font.bold: true
                                wrapMode: Text.Wrap
                            }

                            Label {
                                width: parent.width
                                text: detailRow.modelData.detailText || detailRow.modelData.displayText
                                color: Constants.textColor
                                font.family: Constants.technicalFont
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                            }
                        }
                    }
                }
            }
        }
    }
}
