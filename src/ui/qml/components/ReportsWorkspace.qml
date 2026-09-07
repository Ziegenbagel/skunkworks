pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    property var reportsData: ({})
    property bool autoReportsEnabled: false
    property string selectedDailyReportId: ""
    property double currentEpochMs: Date.now()
    property double dailyScrollOffsetToRestore: -1
    signal autoReportsChanged(bool enabled)
    signal deleteRequested(string reportId)
    signal favoriteChanged(string reportId, bool favorited)

    function archiveSearchText(row) {
        return [
            row.kind, row.domain, row.status, row.title, row.probeName,
            row.detail, root.localTimestamp(row.timestamp), row.timestamp
        ].map(value => String(value || "")).join(" ").toLowerCase();
    }

    function selectedDailyReport() {
        const selected = (reportsData.daily || []).find(
            row => String(row.id || "") === selectedDailyReportId
        );
        return selected || ({});
    }

    function matchingArchive() {
        const needle = archiveSearch.text.trim().toLowerCase();
        const domain = archiveDomain.currentText;
        const status = archiveStatus.currentText;
        const rangeDays = [0, 1, 7, 30][archiveDateRange.currentIndex];
        const cutoff = rangeDays > 0 ? currentEpochMs - rangeDays * 86400000 : 0;
        const rows = (reportsData.archive || []).filter(row => {
            if (domain !== "ALL DOMAINS" && String(row.domain || "").toUpperCase() !== domain) return false;
            if (status !== "ALL STATUSES" && String(row.status || "").toUpperCase() !== status) return false;
            if (cutoff > 0) {
                const timestamp = new Date(String(row.timestamp || "")).getTime();
                if (isNaN(timestamp) || timestamp < cutoff) return false;
            }
            if (!needle.length) return true;
            return root.archiveSearchText(row).indexOf(needle) >= 0;
        });
        const mode = archiveSort.currentIndex;
        return rows.slice().sort((left, right) => {
            if (mode === 0 || mode === 1) {
                const delta = new Date(String(left.timestamp || "")).getTime() - new Date(String(right.timestamp || "")).getTime();
                return mode === 0 ? -delta : delta;
            }
            if (mode === 2 || mode === 3) {
                const leftMissing = left.amount === undefined || left.amount === null;
                const rightMissing = right.amount === undefined || right.amount === null;
                if (leftMissing !== rightMissing) return leftMissing ? 1 : -1;
                const delta = Number(left.amount) - Number(right.amount);
                return mode === 2 ? -delta : delta;
            }
            const keys = mode === 4 ? [left.probeName, right.probeName]
                       : mode === 5 ? [left.title, right.title]
                       : [left.status, right.status];
            return String(keys[0] || "").localeCompare(String(keys[1] || ""));
        });
    }

    function localTimestamp(value) {
        if (!value) return "TIME UNAVAILABLE";
        const parsed = new Date(String(value));
        if (isNaN(parsed.getTime())) return String(value);
        return parsed.toLocaleString(Qt.locale(), Locale.ShortFormat);
    }

    function retentionLabel(report) {
        if (Boolean(report.favorited)) return "FAVORITED · AUTO DELETE OFF";
        const deletion = new Date(String(report.deletesAt || ""));
        if (isNaN(deletion.getTime())) return "AUTO DELETE DATE UNAVAILABLE";
        const days = Math.max(0, Math.ceil((deletion.getTime() - currentEpochMs) / 86400000));
        const timing = days === 0 ? "TODAY" : "IN " + days + (days === 1 ? " DAY" : " DAYS");
        return "AUTO DELETING " + timing + " AT 17:00 · " + deletion.toLocaleDateString(Qt.locale(), Locale.ShortFormat);
    }

    function retentionWarningVisible(report) {
        if (Boolean(report.favorited)) return false;
        const deletion = new Date(String(report.deletesAt || ""));
        if (isNaN(deletion.getTime())) return false;
        const remaining = deletion.getTime() - currentEpochMs;
        return remaining >= 0 && remaining <= 5 * 86400000;
    }

    Timer {
        interval: 60000
        repeat: true
        running: root.visible
        triggeredOnStart: true
        onTriggered: root.currentEpochMs = Date.now()
    }

    TabBar {
        id: reportTabs
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        TabButton { text: "DAILY REPORTS" }
        TabButton { text: "INDUSTRIAL ANALYSIS" }
        TabButton { text: "OPERATIONAL ARCHIVE" }
    }
    StackLayout {
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: reportTabs.bottom; anchors.bottom: parent.bottom
        anchors.topMargin: 12; currentIndex: reportTabs.currentIndex
        Item {
            ColumnLayout {
                anchors.fill: parent; spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "LOCAL DAILY OPERATIONS REPORTS"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
                    Item { Layout.fillWidth: true }
                    CheckBox { text: "GENERATE DAILY REPORTS"; checked: root.autoReportsEnabled; onToggled: root.autoReportsChanged(checked) }
                }
                Label { Layout.fillWidth: true; text: "Generated locally after 17:00 using retained telemetry and accepted game commands. Reports no longer consume game Logbook pages. Unfavorited daily reports are automatically deleted after 30 days."; color: Constants.mutedTextColor; wrapMode: Text.Wrap }
                Label { Layout.fillWidth: true; visible: (root.reportsData.daily || []).length === 0; text: root.autoReportsEnabled ? "NO LOCAL DAILY REPORT IS STORED YET · THE NEXT ELIGIBLE DEFAULT-PROBE REFRESH WILL GENERATE THE LATEST REPORT DUE AFTER 17:00." : "DAILY REPORT GENERATION IS OFF · ENABLE IT ABOVE TO STORE FUTURE REPORTS LOCALLY."; color: Constants.warningColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                RowLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 12
                    Rectangle {
                        Layout.preferredWidth: Math.max(360, root.width * 0.32)
                        Layout.fillHeight: true
                        color: Constants.raisedColor
                        border.color: Constants.lineColor
                        radius: 4
                        ListView {
                            id: dailyList
                            anchors.fill: parent
                            anchors.margins: 8
                            clip: true
                            spacing: 8
                            model: root.reportsData.daily || []
                            onCountChanged: {
                                if (root.dailyScrollOffsetToRestore < 0) return;
                                const offset = root.dailyScrollOffsetToRestore;
                                Qt.callLater(function() {
                                    dailyList.contentY = Math.max(
                                        dailyList.originY,
                                        Math.min(offset, dailyList.originY + Math.max(0, dailyList.contentHeight - dailyList.height))
                                    );
                                    root.dailyScrollOffsetToRestore = -1;
                                });
                            }
                            delegate: Rectangle {
                                id: dailyCard; required property var modelData
                                width: dailyList.width; height: 88
                                color: String(dailyCard.modelData.id || "") === root.selectedDailyReportId ? Constants.selectedColor : Constants.panelColor
                                border.color: Boolean(dailyCard.modelData.favorited) ? Constants.warningColor : Constants.lineColor
                                radius: 4
                                Item {
                                    anchors.left: parent.left; anchors.right: favoriteButton.left
                                    anchors.top: parent.top; anchors.bottom: parent.bottom; anchors.margins: 12
                                    Label {
                                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                                        anchors.bottom: retentionWarning.visible ? retentionWarning.top : parent.bottom
                                        text: String(dailyCard.modelData.title || "Daily report")
                                        color: Constants.textColor; font.family: Constants.technicalFont
                                        wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                    Label {
                                        id: retentionWarning
                                        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                                        height: 18
                                        visible: root.retentionWarningVisible(dailyCard.modelData)
                                        text: root.retentionLabel(dailyCard.modelData)
                                        color: Constants.criticalColor
                                        font.family: Constants.technicalFont; font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: root.selectedDailyReportId = String(dailyCard.modelData.id || "") }
                                }
                                ToolButton {
                                    id: favoriteButton
                                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 8
                                    text: Boolean(dailyCard.modelData.favorited) ? "★" : "☆"
                                    ToolTip.visible: hovered
                                    ToolTip.text: Boolean(dailyCard.modelData.favorited) ? "Remove favorite" : "Favorite and keep beyond 30 days"
                                    onClicked: root.favoriteChanged(String(dailyCard.modelData.id || ""), !Boolean(dailyCard.modelData.favorited))
                                }
                            }
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                Layout.fillWidth: true
                                text: Boolean(root.selectedDailyReport().favorited) ? "★ FAVORITED · RETAINED UNTIL DELETED" : "UNFAVORITED · AUTOMATIC 30-DAY RETENTION"
                                visible: root.selectedDailyReportId.length > 0
                                color: Boolean(root.selectedDailyReport().favorited) ? Constants.warningColor : Constants.mutedTextColor
                                font.family: Constants.technicalFont
                            }
                            Button {
                                text: Boolean(root.selectedDailyReport().favorited) ? "REMOVE FAVORITE" : "FAVORITE"
                                enabled: root.selectedDailyReportId.length > 0
                                onClicked: root.favoriteChanged(root.selectedDailyReportId, !Boolean(root.selectedDailyReport().favorited))
                            }
                            Button {
                                text: "DELETE REPORT"
                                enabled: root.selectedDailyReportId.length > 0
                                onClicked: deleteDialog.open()
                            }
                        }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            TextArea {
                                id: dailyContent; readOnly: true; wrapMode: TextEdit.Wrap
                                text: String(root.selectedDailyReport().content || "")
                                placeholderText: "Select a daily report"; padding: 16
                                background: Rectangle { color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4 }
                            }
                        }
                    }
                }
            }
        }
        Item {
            ColumnLayout {
                anchors.fill: parent; spacing: 12
                Label { text: "INDUSTRIAL ANALYSIS · RETAINED HISTORY"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
                Label { Layout.fillWidth: true; text: "MEASURED values count retained Skunkworks command records. Throughput, depletion, bottleneck and return-on-investment estimates will appear only when sufficient observations exist."; color: Constants.mutedTextColor; wrapMode: Text.Wrap }
                Label { Layout.fillWidth: true; visible: ((root.reportsData.industrial || {}).measuredTotals || []).length === 0; text: "NO RETAINED COMMAND RESULTS ARE AVAILABLE YET · ANALYSIS POPULATES FROM SKUNKWORKS ACTION-JOURNAL RECORDS, NOT FROM EXTRA GAME API REQUESTS."; color: Constants.warningColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                GroupBox {
                    title: "MEASURED COMMAND TOTALS"; Layout.fillWidth: true
                    Flow { width: parent.width; spacing: 10; Repeater { model: (root.reportsData.industrial || {}).measuredTotals || []; delegate: Label { required property var modelData; text: modelData.category.toUpperCase() + " · " + modelData.status + " · " + modelData.count; color: Constants.textColor; font.family: Constants.technicalFont; padding: 10; background: Rectangle { color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4 } } } }
                }
                GroupBox {
                    title: "PROBE ACTIVITY"; Layout.fillWidth: true; Layout.fillHeight: true
                    ListView { anchors.fill: parent; clip: true; spacing: 8; model: (root.reportsData.industrial || {}).probeActivity || []; delegate: Rectangle { id: activityCard; required property var modelData; width: ListView.view.width; height: 64; color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4; Label { anchors.fill: parent; anchors.margins: 10; text: String(activityCard.modelData.probeName).toUpperCase() + " · " + activityCard.modelData.orders + " RECORDED ORDERS\n" + activityCard.modelData.breakdown; color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap } } }
                }
            }
        }
        Item {
            ColumnLayout {
                anchors.fill: parent; spacing: 10
                Label { text: "OPERATIONAL ARCHIVE"; color: Constants.cyanColor; font.family: Constants.displayFont; font.pixelSize: 18; font.bold: true }
                Label { Layout.fillWidth: true; text: "Search one local timeline of recorded commands, long-running operations, and generated reports. This is historical evidence for review and troubleshooting; it never sends commands or replaces live game validation."; color: Constants.mutedTextColor; wrapMode: Text.Wrap }
                RowLayout { Layout.fillWidth: true; TextField { id: archiveSearch; Layout.fillWidth: true; placeholderText: "Search names, resources, quantities, sectors, reasons, status, dates, or reports" } ComboBox { id: archiveDomain; model: ["ALL DOMAINS", "MINING", "PRODUCTION", "TRAVEL", "MAINTENANCE", "OPERATIONS", "REPORTS"] } ComboBox { id: archiveStatus; model: ["ALL STATUSES", "PROPOSED", "APPROVED", "STARTED", "SUCCEEDED", "COMPLETED", "FAILED", "REJECTED", "CANCELLED", "BLOCKED", "RECORDED"] } }
                RowLayout { Layout.fillWidth: true; Label { text: "DATE RANGE"; color: Constants.mutedTextColor; font.family: Constants.technicalFont } ComboBox { id: archiveDateRange; model: ["ALL TIME", "LAST 24 HOURS", "LAST 7 DAYS", "LAST 30 DAYS"] } Label { text: "SORT BY"; color: Constants.mutedTextColor; font.family: Constants.technicalFont } ComboBox { id: archiveSort; model: ["NEWEST FIRST", "OLDEST FIRST", "AMOUNT HIGH–LOW", "AMOUNT LOW–HIGH", "PROBE NAME", "OPERATION", "STATUS"] } Item { Layout.fillWidth: true } Label { text: root.matchingArchive().length + " MATCHING RECORDS"; color: Constants.mutedTextColor; font.family: Constants.technicalFont } }
                Label { Layout.fillWidth: true; visible: root.matchingArchive().length === 0; text: (root.reportsData.archive || []).length === 0 ? "NO LOCAL OPERATIONAL HISTORY IS AVAILABLE YET." : "NO ARCHIVE RECORDS MATCH THE CURRENT SEARCH AND DOMAIN FILTER."; color: Constants.warningColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                ListView {
                    id: archiveList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 8; model: root.matchingArchive()
                    delegate: Rectangle {
                        id: archiveCard; required property var modelData
                        width: archiveList.width; height: Math.max(104, archiveDetails.implicitHeight + 22)
                        color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4
                        Column {
                            id: archiveDetails
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 11; spacing: 4
                            Label { width: parent.width; text: archiveCard.modelData.kind + " · " + archiveCard.modelData.domain.toUpperCase() + " · " + archiveCard.modelData.status; color: Constants.cyanColor; font.family: Constants.technicalFont; elide: Text.ElideRight }
                            Label { width: parent.width; text: archiveCard.modelData.title + " · " + archiveCard.modelData.probeName; color: Constants.textColor; font.bold: true; elide: Text.ElideRight }
                            Label { width: parent.width; text: "LOCAL · " + root.localTimestamp(archiveCard.modelData.timestamp); color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                            Label { width: parent.width; visible: String(archiveCard.modelData.detail || "").length > 0; text: String(archiveCard.modelData.detail || ""); color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: deleteDialog
        anchors.centerIn: parent
        modal: true
        title: "DELETE LOCAL DAILY REPORT?"
        standardButtons: Dialog.Yes | Dialog.Cancel
        Label {
            width: 440
            text: "This permanently deletes the selected report from local Skunkworks storage. It does not affect the game Logbook."
            color: Constants.textColor
            wrapMode: Text.Wrap
        }
        onAccepted: {
            const reportId = root.selectedDailyReportId;
            root.dailyScrollOffsetToRestore = dailyList.contentY;
            root.selectedDailyReportId = "";
            root.deleteRequested(reportId);
        }
    }
}
