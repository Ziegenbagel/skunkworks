import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root
    property alias xControl: xValue
    property alias yControl: yValue
    property alias zControl: zValue
    readonly property bool valid: (xValue.value + yValue.value + zValue.value) % 2 === 0
    spacing: 8
    Label { text: "X" }
    SpinBox { id: xValue; from: -9999; to: 9999; editable: true }
    Label { text: "Y" }
    SpinBox { id: yValue; from: -9999; to: 9999; editable: true }
    Label { text: "Z" }
    SpinBox { id: zValue; from: -9999; to: 9999; editable: true }
    Label { text: (xValue.value + yValue.value + zValue.value) % 2 === 0 ? "VALID FCC" : "INVALID FCC"; color: (xValue.value + yValue.value + zValue.value) % 2 === 0 ? "#55c28a" : "#d95f59" }
}
