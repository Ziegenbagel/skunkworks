pragma Singleton
import QtQuick

QtObject {
    // 1080p is the authoring baseline. Qt's device-independent pixels and the
    // responsive layout in MissionControlScreen also cover HiDPI/4K displays.
    readonly property int width: 1920
    readonly property int height: 1080
    readonly property int minimumWidth: 1280
    readonly property int minimumHeight: 720

    readonly property color voidColor: "#080d12"
    readonly property color panelColor: "#101922"
    readonly property color raisedColor: "#16232e"
    readonly property color selectedColor: "#1b3240"
    readonly property color lineColor: "#294553"
    readonly property color cyanColor: "#55c7d9"
    readonly property color blueColor: "#4389c7"
    readonly property color textColor: "#d7e5ea"
    readonly property color mutedTextColor: "#8298a3"
    readonly property color nominalColor: "#55c28a"
    readonly property color noticeColor: "#6ba8d9"
    readonly property color warningColor: "#d7a64a"
    readonly property color criticalColor: "#d95f59"

    readonly property string displayFont: "Copperplate"
    readonly property string bodyFont: "Inter"
    readonly property string technicalFont: "Menlo"
}
