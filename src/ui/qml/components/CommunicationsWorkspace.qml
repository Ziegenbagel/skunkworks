pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var communicationsData: ({})
    property var logbookData: ({})
    property var probes: []
    property int focusedProbeId: -1
    signal messageSendRequested(var payload)
    signal messageReadRequested(string messageId)
    signal logbookCreateRequested(string title, string content)
    signal logbookUpdateRequested(int pageId, string title, string content)
    signal logbookDeleteRequested(int pageId)
    signal autoLogbookChanged(bool enabled)
    signal logbookPageOpenRequested(int pageId)

    TabBar {
        id: tabs
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        TabButton { text: "MESSAGING · " + Number(root.communicationsData.unreadCount || 0) + " UNREAD" }
        TabButton { text: "LOGBOOK" }
    }
    StackLayout {
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: tabs.bottom; anchors.bottom: parent.bottom
        anchors.topMargin: 12; currentIndex: tabs.currentIndex
        Item {
            ColumnLayout {
                anchors.fill: parent; spacing: 12
                Label { text: "PROBE COMMUNICATIONS"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "TO"; color: Constants.textColor; font.family: Constants.technicalFont }
                    ComboBox { id: recipient; Layout.preferredWidth: 280; model: root.probes.filter(probe => Number(probe.id) !== root.focusedProbeId); textRole: "name"; valueRole: "id" }
                    TextField { id: subject; Layout.fillWidth: true; placeholderText: "Subject" }
                    Button {
                        text: "SEND MESSAGE"; enabled: recipient.currentIndex >= 0 && body.text.trim().length > 0
                        onClicked: {
                            root.messageSendRequested({"recipient":{"type":"probe","id":Number(recipient.currentValue)},"subject":subject.text,"body":body.text});
                            subject.clear(); body.clear();
                        }
                    }
                }
                TextArea { id: body; Layout.fillWidth: true; Layout.preferredHeight: 100; placeholderText: "Message body…"; wrapMode: TextEdit.Wrap; background: Rectangle { color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4 } }
                RowLayout {
                    Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
                    GroupBox {
                        title: "INBOX"; Layout.fillWidth: true; Layout.fillHeight: true
                        ListView {
                            anchors.fill: parent; clip: true; spacing: 8; model: root.communicationsData.inbox || []
                            delegate: Rectangle {
                                id: inboxCard; required property var modelData
                                width: ListView.view.width; height: inboxText.implicitHeight + 26
                                color: Boolean(modelData.read || modelData.isRead || modelData.status === "read") ? Constants.raisedColor : Constants.selectedColor
                                border.color: Constants.lineColor; radius: 4
                                Label { id: inboxText; anchors.fill: parent; anchors.margins: 13; text: String(inboxCard.modelData.subject || inboxCard.modelData.title || "MESSAGE") + "\n" + String(inboxCard.modelData.body || inboxCard.modelData.content || "") ; color: Constants.textColor; wrapMode: Text.Wrap; font.family: Constants.technicalFont }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: if (!Boolean(inboxCard.modelData.read || inboxCard.modelData.isRead || inboxCard.modelData.status === "read")) root.messageReadRequested(String(inboxCard.modelData.id)) }
                            }
                        }
                    }
                    GroupBox {
                        title: "SENT"; Layout.fillWidth: true; Layout.fillHeight: true
                        ListView {
                            anchors.fill: parent; clip: true; spacing: 8; model: root.communicationsData.outbox || []
                            delegate: Rectangle { id: sentCard; required property var modelData; width: ListView.view.width; height: sentText.implicitHeight + 26; color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4
                                Label { id: sentText; anchors.fill: parent; anchors.margins: 13; text: String(sentCard.modelData.subject || sentCard.modelData.title || "MESSAGE") + "\n" + String(sentCard.modelData.body || sentCard.modelData.content || ""); color: Constants.textColor; wrapMode: Text.Wrap; font.family: Constants.technicalFont }
                            }
                        }
                    }
                }
            }
        }
        LogbookWorkspace {
            logbookData: root.logbookData
            onCreateRequested: (title, content) => root.logbookCreateRequested(title, content)
            onUpdateRequested: (pageId, title, content) => root.logbookUpdateRequested(pageId, title, content)
            onDeleteRequested: pageId => root.logbookDeleteRequested(pageId)
            onAutoLoggingChanged: enabled => root.autoLogbookChanged(enabled)
            onPageOpenRequested: pageId => root.logbookPageOpenRequested(pageId)
        }
    }
}
