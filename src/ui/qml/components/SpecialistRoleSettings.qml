pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ColumnLayout {
    id: root
    property string role: ""
    property var settings: ({})
    property var runtime: ({})
    property var hubs: []
    readonly property bool combat: role === "missile_destroyer"
    signal saveRequested(var settings)
    Layout.fillWidth: true
    spacing: 12

    function save(startMission, returnHome) {
        const value = Object.assign({}, root.settings, {
            infrastructureEnabled: enabledRole.checked,
            hubProbeId: hub.currentIndex >= 0 ? Number(root.hubs[hub.currentIndex].id) : -1,
            home: {x:Number(homeX.text), y:Number(homeY.text), z:Number(homeZ.text)},
            returnHome: returnHome,
            combatAuthorized: combatConsent.checked,
            missileStock: stock.value,
            targetSector: {x:Number(targetX.text), y:Number(targetY.text), z:Number(targetZ.text)},
            lostObjectIds: lostIds.text.split(",").map(s => s.trim()).filter(s => s.length > 0)
        });
        if (startMission)
            value.missionId = String(Date.now()) + "-" + String(Math.random());
        root.saveRequested(value);
    }
    Label {
        Layout.fillWidth: true
        text: root.combat ? "MISSILE DESTROYER" : "SALVAGE PROBE"
        color: Constants.cyanColor; font.bold: true
    }
    CheckBox { id: enabledRole; text: "Enable role automation"; checked: Boolean(root.settings.infrastructureEnabled) }
    Label {
        Layout.fillWidth: true; wrapMode: Text.Wrap; color: Constants.textColor
        text: root.combat
            ? "Travel to your assigned sector and attack identified Others ships. Wait for each missile result before firing again. Return when empty or no eligible targets remain, refill at the Hub, then wait for your next mission."
            : "Recover unclaimed drifting containers and loose items within known SCUT coverage. Return recovered cargo to the selected Hub. Active workflow reservations and travel-safe storage limits remain protected."
    }
    Label { text: "HOME HUB"; color: Constants.textColor }
    ComboBox {
        id: hub; Layout.fillWidth: true
        model: root.hubs; textRole: "name"
        currentIndex: root.hubs.findIndex(p => Number(p.id) === Number(root.settings.hubProbeId))
    }
    Label { text: "HOME SECTOR · X / Y / Z"; color: Constants.textColor }
    RowLayout {
        Layout.fillWidth: true
        TextField { id: homeX; Layout.fillWidth: true; text: String((root.settings.home || {}).x ?? 0); validator: IntValidator {} }
        TextField { id: homeY; Layout.fillWidth: true; text: String((root.settings.home || {}).y ?? 0); validator: IntValidator {} }
        TextField { id: homeZ; Layout.fillWidth: true; text: String((root.settings.home || {}).z ?? 0); validator: IntValidator {} }
    }
    Label { visible: root.combat; text: "MISSION SECTOR · X / Y / Z"; color: Constants.textColor }
    RowLayout {
        visible: root.combat; Layout.fillWidth: true
        TextField { id: targetX; Layout.fillWidth: true; text: String((root.settings.targetSector || {}).x ?? 0); validator: IntValidator {} }
        TextField { id: targetY; Layout.fillWidth: true; text: String((root.settings.targetSector || {}).y ?? 0); validator: IntValidator {} }
        TextField { id: targetZ; Layout.fillWidth: true; text: String((root.settings.targetSector || {}).z ?? 0); validator: IntValidator {} }
    }
    RowLayout {
        visible: root.combat
        Label { text: "Missiles per refill"; color: Constants.textColor }
        SpinBox { id: stock; from: 1; to: 100; value: Number(root.settings.missileStock || 10); editable: true }
    }
    CheckBox {
        id: combatConsent; visible: root.combat
        text: "Authorize automatic missile attacks on Others ships in my assigned sector"
        checked: Boolean(root.settings.combatAuthorized)
    }
    Label { visible: !root.combat; text: "PRIORITY LOST OBJECT IDS · OPTIONAL, COMMA-SEPARATED"; color: Constants.textColor }
    TextField { id: lostIds; visible: !root.combat; Layout.fillWidth: true; text: (root.settings.lostObjectIds || []).join(", ") }
    Label {
        Layout.fillWidth: true; wrapMode: Text.Wrap; color: Constants.cyanColor
        text: "STATUS · " + String(root.runtime.phase || "not_evaluated").replace(/_/g, " ").toUpperCase()
              + "\n" + String(root.runtime.summary || "Save settings and evaluate an automation cycle.")
    }
    RowLayout {
        Layout.fillWidth: true
        Button { text: "SAVE / RESUME ROLE"; onClicked: root.save(false, false) }
        Button { visible: root.combat; text: "START NEW SECTOR MISSION"; enabled: enabledRole.checked && combatConsent.checked; onClicked: root.save(true, false) }
        Button { text: "RETURN HOME"; onClicked: root.save(false, true) }
    }
}
