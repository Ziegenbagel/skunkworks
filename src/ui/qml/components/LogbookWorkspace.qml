pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var logbookData: ({})
    property int selectedPageId: -1
    signal createRequested(string title, string content)
    signal updateRequested(int pageId, string title, string content)
    signal deleteRequested(int pageId)
    signal autoLoggingChanged(bool enabled)
    signal pageOpenRequested(int pageId)

    function selectPage(page) {
        selectedPageId = Number(page.id);
        titleEditor.text = page.title || "";
        contentEditor.text = page.content || "";
    }
    function clearEditor() { selectedPageId = -1; titleEditor.clear(); contentEditor.clear(); }
    onLogbookDataChanged: {
        if (selectedPageId < 0) return;
        const pages = logbookData.pages || [];
        let found = false;
        for (let i = 0; i < pages.length; ++i) {
            if (Number(pages[i].id) === selectedPageId && pages[i].content !== undefined) {
                found = true;
                titleEditor.text = pages[i].title || "";
                contentEditor.text = pages[i].content || "";
                break;
            }
        }
        if (!found) clearEditor();
    }

    RowLayout {
        anchors.fill: parent; spacing: 18
        ColumnLayout {
            Layout.preferredWidth: Math.max(360, root.width * 0.32); Layout.fillHeight: true; spacing: 10
            Label { text: "FOCUSED PROBE LOGBOOK"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
            Button { text: "+ NEW PAGE"; onClicked: root.clearEditor() }
            ListView {
                id: pageList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8; model: root.logbookData.pages || []
                delegate: Rectangle {
                    id: pageCard; required property var modelData; required property int index
                    width: pageList.width; height: 92; color: Number(modelData.id) === root.selectedPageId ? Constants.selectedColor : Constants.raisedColor; border.color: Number(modelData.id) === root.selectedPageId || Boolean(modelData.isNewDailyReport) ? Constants.cyanColor : Constants.lineColor; border.width: Boolean(modelData.isNewDailyReport) ? 2 : 1; radius: 4
                    Column { anchors.fill: parent; anchors.margins: 13; spacing: 6
                        Label { width: parent.width; text: (Boolean(pageCard.modelData.isNewDailyReport) ? "NEW · " : "") + (pageCard.modelData.title || "Untitled"); color: Boolean(pageCard.modelData.isNewDailyReport) ? Constants.cyanColor : Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true; elide: Text.ElideRight }
                        Label { width: parent.width; text: "PROBE · " + String(pageCard.modelData.sourceProbeName || pageCard.modelData.probeId || "Unknown").toUpperCase(); color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 11; elide: Text.ElideRight }
                        Label { width: parent.width; text: "UPDATED · " + (pageCard.modelData.updatedAt || "Unknown"); color: Constants.mutedTextColor; font.pixelSize: 12; elide: Text.ElideRight }
                    }
                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: { root.selectPage(pageCard.modelData); root.pageOpenRequested(Number(pageCard.modelData.id)); } }
                }
            }
        }
        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Constants.lineColor }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Label { text: root.selectedPageId >= 0 ? "EDIT LOGBOOK PAGE" : "NEW LOGBOOK PAGE"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
                Item { Layout.fillWidth: true }
                CheckBox { text: "AUTO-LOG DAILY ROLE REPORTS AND MAJOR DISCOVERIES"; checked: Boolean(root.logbookData.autoLoggingEnabled); onToggled: root.autoLoggingChanged(checked) }
            }
            Label { Layout.fillWidth: true; text: "Auto-logging is opt-in. At the first refresh after 17:00 local time, Skunkworks creates one role-specific daily game-logbook report per probe, plus pages for major discoveries."; color: Constants.mutedTextColor; font.pixelSize: 13; wrapMode: Text.Wrap }
            TextField { id: titleEditor; Layout.fillWidth: true; placeholderText: "Page title"; maximumLength: 120; font.pixelSize: 16 }
            ScrollView {
                id: contentScroller
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                TextArea {
                    id: contentEditor
                    width: contentScroller.availableWidth
                    placeholderText: "Write a probe logbook note…"
                    wrapMode: TextEdit.Wrap
                    font.pixelSize: 15
                    padding: 16
                    background: Rectangle { color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4 }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Button { text: "DELETE PAGE"; visible: root.selectedPageId >= 0; onClicked: deleteConfirmation.open() }
                Item { Layout.fillWidth: true }
                Button { text: root.selectedPageId >= 0 ? "SAVE CHANGES" : "CREATE PAGE"; enabled: titleEditor.text.trim().length > 0 && contentEditor.text.trim().length > 0; onClicked: { if (root.selectedPageId >= 0) root.updateRequested(root.selectedPageId, titleEditor.text, contentEditor.text); else root.createRequested(titleEditor.text, contentEditor.text); } }
            }
        }
    }
    Dialog { id: deleteConfirmation; anchors.centerIn: parent; modal: true; title: "DELETE LOGBOOK PAGE?"; standardButtons: Dialog.Yes | Dialog.No; onAccepted: { root.deleteRequested(root.selectedPageId); root.clearEditor(); } Label { width: 420; text: "This permanently deletes the selected page from the game logbook."; color: Constants.textColor; wrapMode: Text.Wrap } }
}
