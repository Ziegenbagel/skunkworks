pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Item {
    id: root
    readonly property var activeTravelTarget: (root.automationData || {}).travelTarget || ({})
    property var navigationData: ({})
    property var travelPreview: ({})
    property var automationData: ({})
    property var focusedProbe: ({})
    property var availableProbes: []
    signal previewRequested(int x, int y, int z, string routeMode)
    signal executeRequested(bool riskAcknowledged)
    signal cancelMovementRequested()
    signal scanRequested(int x, int y, int z)
    signal neighborScanRequested()
    signal autonomousTargetRequested(int x, int y, int z, string routeMode)
    signal autonomousTargetCancelRequested()
    signal transportCycleRequested(var plan)
    signal transportCycleStartRequested(string operationId)
    signal transportCyclePauseRequested(string operationId)
    signal transportCycleDeleteRequested(string operationId)
    property var selectedTransportCycle: ({})

    readonly property string focusedRole: String((automationData.probeRoles || {})[String(focusedProbe.probeId)] || "unassigned")
    readonly property bool transportEligible: focusedRole === "transport" || focusedRole === "deuterium_tanker"
    readonly property bool tankerEligible: focusedRole === "deuterium_tanker" || String(focusedProbe.model) === "deuterium_tanker"
    readonly property bool validManualCoordinates: validCoordinates(manualX.value, manualY.value, manualZ.value)
    readonly property bool validTransportCoordinates: sourceCoordinates.valid && deliveryCoordinates.valid && returnCoordinates.valid && (!refuelEnabled.checked || refuelCoordinates.valid)
    function validCoordinates(x, y, z) { return (Number(x) + Number(y) + Number(z)) % 2 === 0; }
    function coordinates(x, y, z) { return {"x": Number(x), "y": Number(y), "z": Number(z)}; }
    function coordinateLabel(value) {
        value = value || {};
        return "FCC " + Number(value.x || 0) + " / " + Number(value.y || 0) + " / " + Number(value.z || 0);
    }
    function chooseSector(sector) {
        manualX.value = Number(sector.x); manualY.value = Number(sector.y); manualZ.value = Number(sector.z);
        navigationTabs.currentIndex = 0;
    }
    function transportPayload() {
        return {
            "probeId": Number(focusedProbe.probeId),
            "resourceType": String(resourceType.currentValue),
            "loadSourceMode": String(loadSourceMode.currentValue),
            "source": coordinates(sourceCoordinates.xControl.value, sourceCoordinates.yControl.value, sourceCoordinates.zControl.value),
            "destination": coordinates(deliveryCoordinates.xControl.value, deliveryCoordinates.yControl.value, deliveryCoordinates.zControl.value),
            "returnPoint": coordinates(returnCoordinates.xControl.value, returnCoordinates.yControl.value, returnCoordinates.zControl.value),
            "loadUntilPercent": loadThreshold.value,
            "unloadUntilPercent": unloadThreshold.value,
            "protectedDeuterium": protectedFuel.value,
            "reserveHops": reserveHops.value,
            "repeat": repeatCycle.checked,
            "refuelEnabled": refuelEnabled.checked,
            "refuelSector": coordinates(refuelCoordinates.xControl.value, refuelCoordinates.yControl.value, refuelCoordinates.zControl.value),
            "minimumRefuelSourceAmount": minimumRefuelAmount.value
            ,"sourceProbeId": loadSourceMode.currentValue === "probe" ? (sourceProbe.currentValue || null) : null
            ,"destinationProbeId": destinationProbe.currentValue || null
            ,"loadAmount": root.tankerEligible && resourceType.currentValue === "deuterium" ? loadAmount.value : null
            ,"unloadAmount": null
        };
    }

    ColumnLayout {
        anchors.fill: parent; spacing: 12
        RowLayout {
            Layout.fillWidth: true
            Label { text: "FOCUSED PROBE NAVIGATION"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true; font.pixelSize: 15 }
            Item { Layout.fillWidth: true }
            Label { text: root.navigationData.current ? root.navigationData.current.label : "SECTOR UNKNOWN"; color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true; font.pixelSize: 14 }
            Label { text: root.focusedRole.replace("_", " ").toUpperCase(); color: root.transportEligible ? Constants.nominalColor : Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 13 }
            Label { text: Math.round(root.navigationData.fuelPercent || 0) + "% FUEL"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 13 }
        }

        TabBar {
            id: navigationTabs
            Layout.fillWidth: true
            TabButton { text: "MANUAL TRAVEL" }
            TabButton { text: "TRANSPORT AUTOMATION" }
            TabButton { text: "SECTOR SCANNING" }
        }

        StackLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            currentIndex: navigationTabs.currentIndex

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width - 20; spacing: 16
                    GroupBox {
                        visible: Boolean(root.focusedProbe.canCancelMovement)
                        title: "ACTIVE MOVEMENT · PREPARATION CANCELLATION"; Layout.fillWidth: true
                        RowLayout {
                            anchors.fill: parent; spacing: 16
                            Label {
                                Layout.fillWidth: true
                                text: "This probe is still preparing its jump. Cancellation is available only during this phase and refunds the reserved deuterium."
                                color: Constants.warningColor; font.pixelSize: 14; wrapMode: Text.Wrap
                            }
                            Button {
                                text: "CANCEL PREPARING MOVEMENT"
                                onClicked: root.cancelMovementRequested()
                            }
                        }
                    }
                    GroupBox {
                        title: "ONE-TIME MANUAL TRAVEL ORDER"; Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent; spacing: 14
                            Label { Layout.fillWidth: true; text: "Preview and confirm a single movement command for the focused probe. This does not create a repeating route."; color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 15; wrapMode: Text.Wrap }
                            RowLayout {
                                spacing: 12
                                Label { text: "DESTINATION FCC"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                                Label { text: "X" } SpinBox { id: manualX; from: -9999; to: 9999; editable: true }
                                Label { text: "Y" } SpinBox { id: manualY; from: -9999; to: 9999; editable: true }
                                Label { text: "Z" } SpinBox { id: manualZ; from: -9999; to: 9999; editable: true }
                                Label { text: root.validManualCoordinates ? "VALID" : "INVALID FCC"; color: root.validManualCoordinates ? Constants.nominalColor : Constants.criticalColor; font.family: Constants.technicalFont; font.bold: true }
                            }
                            RowLayout {
                                Label { text: "ROUTE STRATEGY"; color: Constants.mutedTextColor; font.family: Constants.technicalFont }
                                ComboBox { id: routeMode; model: ["segmented", "direct"]; Layout.preferredWidth: 190 }
                                Button { text: "PREVIEW ROUTE"; enabled: root.validManualCoordinates; onClicked: root.previewRequested(manualX.value, manualY.value, manualZ.value, String(routeMode.currentText)) }
                            }
                        }
                    }
                    GroupBox {
                        title: "MANUAL ROUTE REVIEW"; Layout.fillWidth: true
                        ColumnLayout {
                            anchors.fill: parent; spacing: 10
                            Label { text: root.travelPreview.targetLabel ? "ROUTE TO " + root.travelPreview.targetLabel : "NO ROUTE PREVIEW"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true }
                            Label { Layout.fillWidth: true; text: root.travelPreview.targetLabel ? "Selected " + String(root.travelPreview.selectedRoute).toUpperCase() + " · next command " + root.travelPreview.executionLabel + " · recommended " + String(root.travelPreview.recommendedRoute).toUpperCase() : "Enter a destination above or select a sector from Sector Scanning."; color: Constants.textColor; font.family: Constants.bodyFont; font.pixelSize: 15; wrapMode: Text.Wrap }
                            Label {
                                visible: Boolean(root.travelPreview.targetLabel)
                                Layout.fillWidth: true
                                text: Number(root.travelPreview.hopCount || 0) + " STOP" + (Number(root.travelPreview.hopCount || 0) === 1 ? "" : "S")
                                      + " · GAME ETA BECOMES AVAILABLE AFTER EACH ORDER STARTS"
                                color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true
                            }
                            Repeater {
                                model: root.travelPreview.routeHops || []
                                delegate: Label {
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    text: (index + 1) + ". " + String(modelData.label) + (index === 0 ? " · NEXT COMMAND" : "")
                                    color: index === 0 ? Constants.cyanColor : Constants.textColor
                                    font.family: Constants.technicalFont; font.pixelSize: 14
                                }
                            }
                            Repeater { model: root.travelPreview.hazards || []; delegate: Label { required property var modelData; Layout.fillWidth: true; text: "⚠ " + modelData.message; color: modelData.severity === "critical" ? Constants.criticalColor : Constants.warningColor; font.pixelSize: 14; wrapMode: Text.Wrap } }
                            CheckBox { id: acknowledgeRisk; visible: Boolean(root.travelPreview.acknowledgementRequired); text: "I acknowledge the displayed travel risks" }
                            Button { text: "CONFIRM ONE-TIME TRAVEL COMMAND"; enabled: Boolean(root.travelPreview.canExecute) && (!root.travelPreview.acknowledgementRequired || acknowledgeRisk.checked); onClicked: root.executeRequested(acknowledgeRisk.checked) }
                            Button {
                                text: "SAVE AUTO-TRAVEL DESTINATION"
                                enabled: root.validManualCoordinates && Boolean(root.travelPreview.targetLabel)
                                onClicked: root.autonomousTargetRequested(
                                    manualX.value, manualY.value, manualZ.value,
                                    String(routeMode.currentValue))
                            }
                            Label {
                                Layout.fillWidth: true; wrapMode: Text.Wrap
                                text: "Saves the reviewed segmented route as a durable goal. An order is sent immediately only when execution mode is AUTOMATIC, live orders are enabled, and MOVE PROBE is allowed; otherwise it waits safely in the planner."
                                color: Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 13
                            }
                            Label {
                                visible: Object.keys(root.activeTravelTarget).length > 0
                                Layout.fillWidth: true
                                text: "ACTIVE AUTO-TRAVEL TARGET · FCC " + String(root.activeTravelTarget.x === undefined ? "—" : root.activeTravelTarget.x) + " / " + String(root.activeTravelTarget.y === undefined ? "—" : root.activeTravelTarget.y) + " / " + String(root.activeTravelTarget.z === undefined ? "—" : root.activeTravelTarget.z)
                                color: Constants.nominalColor; font.family: Constants.technicalFont; font.bold: true
                            }
                            Button {
                                visible: Object.keys(root.activeTravelTarget).length > 0
                                text: "CANCEL AUTO-TRAVEL TARGET"
                                onClicked: root.autonomousTargetCancelRequested()
                            }
                        }
                    }
                }
            }

            ScrollView {
                clip: true
                ColumnLayout {
                    width: parent.width - 20; spacing: 16
                    Rectangle {
                        visible: !root.transportEligible; Layout.fillWidth: true; implicitHeight: roleWarning.implicitHeight + 32
                        color: Constants.raisedColor; border.color: Constants.warningColor; radius: 4
                        Label { id: roleWarning; anchors.fill: parent; anchors.margins: 16; text: "TRANSPORT AUTOMATION IS ROLE-GATED\nAssign the focused probe the TRANSPORT or DEUTERIUM TANKER role in Settings before creating a recurring logistics route."; color: Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 16; font.bold: true; wrapMode: Text.Wrap }
                    }
                    GroupBox {
                        visible: root.transportEligible; title: "RECURRING ROUND-TRIP LOGISTICS"; Layout.fillWidth: true
                        GridLayout {
                            anchors.fill: parent; columns: 4; columnSpacing: 18; rowSpacing: 12
                            Label { text: "RESOURCE"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                            ComboBox { id: resourceType; textRole: "text"; valueRole: "value"; model: root.tankerEligible ? [{"text":"DEUTERIUM", "value":"deuterium"}, {"text":"METALS", "value":"metals"}, {"text":"ICE", "value":"ice"}, {"text":"CARBON COMPOUNDS", "value":"carbon_compounds"}] : [{"text":"METALS", "value":"metals"}, {"text":"ICE", "value":"ice"}, {"text":"CARBON COMPOUNDS", "value":"carbon_compounds"}] }
                            CheckBox { id: repeatCycle; text: "REPEAT UNTIL PAUSED"; checked: true }
                            Label { text: "Each departure protects the full loop fuel reserve."; color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 14 }

                            Label { text: "LOADING SECTOR"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.bold: true }
                            CoordinateEditor { id: sourceCoordinates; Layout.columnSpan: 3 }
                            Label { text: "UNLOADING SECTOR"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                            CoordinateEditor { id: deliveryCoordinates; Layout.columnSpan: 3 }
                            Label { text: "RETURN POINT"; color: Constants.cyanColor; font.family: Constants.technicalFont; font.bold: true }
                            CoordinateEditor { id: returnCoordinates; Layout.columnSpan: 3 }

                            Label { text: "LOAD SOURCE"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.bold: true }
                            ComboBox {
                                id: loadSourceMode; Layout.columnSpan: 3; Layout.fillWidth: true
                                textRole: "text"; valueRole: "value"
                                model: [
                                    {"text":"LOAD FROM PROBE", "value":"probe"},
                                    {"text":"MINE IN SECTOR", "value":"mine_in_sector"}
                                ]
                            }
                            Label { visible: loadSourceMode.currentValue === "probe"; text: "LOAD FROM PROBE"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.bold: true }
                            ComboBox { visible: loadSourceMode.currentValue === "probe"; id: sourceProbe; Layout.columnSpan: 3; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: root.availableProbes }
                            Label {
                                visible: loadSourceMode.currentValue === "mine_in_sector"; Layout.columnSpan: 4; Layout.fillWidth: true
                                text: "At the loading sector, the resource planner assigns available Mannys to the selected resource until the load threshold is reached or the observed source is depleted. The delivery leg then resumes automatically."
                                color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 14; wrapMode: Text.Wrap
                            }
                            Label { text: "UNLOAD INTO PROBE"; color: Constants.warningColor; font.family: Constants.technicalFont; font.bold: true }
                            ComboBox { id: destinationProbe; Layout.columnSpan: 3; Layout.fillWidth: true; textRole: "name"; valueRole: "id"; model: root.availableProbes }

                            Label { visible: !(root.tankerEligible && resourceType.currentValue === "deuterium"); text: "LOAD CARGO UNTIL"; color: Constants.textColor; font.family: Constants.technicalFont }
                            RowLayout { visible: !(root.tankerEligible && resourceType.currentValue === "deuterium"); SpinBox { id: loadThreshold; from: 1; to: 100; value: 90; editable: true } Label { text: "% FULL" } }
                            Label { visible: !(root.tankerEligible && resourceType.currentValue === "deuterium"); text: "UNLOAD CARGO UNTIL"; color: Constants.textColor; font.family: Constants.technicalFont }
                            RowLayout { visible: !(root.tankerEligible && resourceType.currentValue === "deuterium"); SpinBox { id: unloadThreshold; from: 0; to: 99; value: 10; editable: true } Label { text: "% REMAINS" } }
                            Label { visible: root.tankerEligible && resourceType.currentValue === "deuterium"; text: "LOAD TANK TO"; color: Constants.textColor; font.family: Constants.technicalFont }
                            RowLayout { visible: root.tankerEligible && resourceType.currentValue === "deuterium"; SpinBox { id: loadAmount; from: 0; to: 800; value: 400; editable: true } Label { text: "ECE (MAX 800)" } }
                            Label { text: "PROTECTED DEUTERIUM"; color: Constants.warningColor; font.family: Constants.technicalFont }
                            RowLayout { SpinBox { id: protectedFuel; from: 0; to: 100; value: 20; editable: true } Label { text: "% FLOOR" } }
                            Label { text: "CONTINGENCY"; color: Constants.textColor; font.family: Constants.technicalFont }
                            RowLayout { SpinBox { id: reserveHops; from: 0; to: 20; value: 1; editable: true } Label { text: "RESERVE HOPS" } }
                        }
                    }
                    GroupBox {
                        visible: root.transportEligible; title: "OPTIONAL VERIFIED REFUEL STOP"; Layout.fillWidth: true
                        RowLayout {
                            anchors.fill: parent; spacing: 14
                            CheckBox { id: refuelEnabled; text: "ROUTE DEPENDS ON REFUELING" }
                            CoordinateEditor { id: refuelCoordinates; enabled: refuelEnabled.checked }
                            Label { text: "MINIMUM SOURCE"; color: Constants.mutedTextColor }
                            SpinBox { id: minimumRefuelAmount; from: 0; to: 100000; editable: true; enabled: refuelEnabled.checked }
                            Label { text: "ECE"; color: Constants.mutedTextColor }
                        }
                    }
                    Button { visible: root.transportEligible; text: "SAVE PLANNED ROUND-TRIP OPERATION"; enabled: root.validTransportCoordinates && unloadThreshold.value <= loadThreshold.value; Layout.alignment: Qt.AlignRight; onClicked: root.transportCycleRequested(root.transportPayload()) }
                    Label { visible: root.transportEligible; Layout.fillWidth: true; text: "Saved cycles are durable planned Operations. Automatic execution remains subject to the execution policy, command allowlist, fresh SCUT/source observations, load and unload thresholds, and return-fuel safety checks."; color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 14; wrapMode: Text.Wrap }
                    Repeater {
                        model: root.automationData.transportCycles || []
                        delegate: Rectangle {
                            id: cycleRow; required property var modelData
                            Layout.fillWidth: true; implicitHeight: cycleLabel.implicitHeight + 28
                            color: Constants.raisedColor; border.color: Constants.lineColor; radius: 4
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 10
                                Label { id: cycleLabel; Layout.fillWidth: true; text: String(cycleRow.modelData.name || "Round Trip Transport").toUpperCase() + " · " + String(cycleRow.modelData.state || "planned").toUpperCase(); color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 15; font.bold: true }
                                Button {
                                    text: "REVIEW"
                                    onClicked: {
                                        root.selectedTransportCycle = cycleRow.modelData;
                                        transportReview.open();
                                    }
                                }
                                Button {
                                    visible: String(cycleRow.modelData.state || "planned") === "active"
                                    text: "PAUSE ROUTE"
                                    onClicked: root.transportCyclePauseRequested(String(cycleRow.modelData.id))
                                }
                            }
                        }
                    }
                }
            }

            Item {
                ColumnLayout {
                    anchors.fill: parent; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Label { Layout.fillWidth: true; text: "Select an adjacent sector to populate Manual Travel, scan one sector, or survey all 12 FCC neighbors. SCUT coverage is calculated from live relay positions."; color: Constants.mutedTextColor; font.family: Constants.bodyFont; font.pixelSize: 15; wrapMode: Text.Wrap }
                        Button { text: "SCAN ALL 12 NEIGHBORING SECTORS"; onClicked: root.neighborScanRequested(); ToolTip.visible: hovered; ToolTip.text: "Runs the same passive observation for every adjacent FCC sector and saves each result to the Skunkworks galaxy map." }
                    }
                    Label { visible: root.focusedRole === "explorer"; Layout.fillWidth: true; text: "EXPLORER AUTOMATION ACTIVE · NEIGHBORS ARE SCANNED ONCE AFTER ARRIVAL IN EACH NEW SECTOR"; color: Constants.nominalColor; font.family: Constants.technicalFont; font.bold: true; wrapMode: Text.Wrap }
                    Label {
                        visible: Boolean(root.navigationData.scanResult)
                        Layout.fillWidth: true
                        text: root.navigationData.scanResult && root.navigationData.scanResult.kind === "neighbor_scan"
                              ? String(root.navigationData.scanResult.label) + " · " + Number(root.navigationData.scanResult.scanned || 0) + "/12 SCANNED · " + Number(root.navigationData.scanResult.discoveries || 0) + " WITH KNOWN OBJECTS" + (Number(root.navigationData.scanResult.failed || 0) ? " · " + Number(root.navigationData.scanResult.failed) + " FAILED" : "")
                              : root.navigationData.scanResult ? String(root.navigationData.scanResult.label || "SECTOR SCAN COMPLETE") + " · " + String(root.navigationData.scanResult.knowledgeLevel || "unknown").replace("_", " ").toUpperCase() : ""
                        color: Number((root.navigationData.scanResult || {}).failed || 0) > 0 ? Constants.warningColor : Constants.cyanColor
                        font.family: Constants.technicalFont; font.bold: true; wrapMode: Text.Wrap
                    }
                    ListView {
                        id: neighborList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 7; model: root.navigationData.neighbors || []
                        delegate: Rectangle {
                            id: neighborRow; required property var modelData; required property int index
                            width: neighborList.width; height: 78; color: neighborMouse.containsMouse ? Constants.selectedColor : index % 2 ? Constants.panelColor : Constants.raisedColor
                            border.color: modelData.scutCoverage && modelData.scutCoverage.covered ? Constants.nominalColor : Constants.lineColor
                            RowLayout { anchors.fill: parent; anchors.margins: 10
                                Label { Layout.preferredWidth: 210; text: neighborRow.modelData.label; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 14; font.bold: true }
                                Label { Layout.preferredWidth: 180; text: String(neighborRow.modelData.knowledgeLevel).split("_").join(" ").toUpperCase(); color: neighborRow.modelData.visited ? Constants.cyanColor : Constants.mutedTextColor; font.family: Constants.technicalFont; font.pixelSize: 13 }
                                ColumnLayout { Layout.fillWidth: true
                                    Label { Layout.fillWidth: true; text: neighborRow.modelData.scanSummary || "Long-range details unavailable"; color: Constants.textColor; font.family: Constants.technicalFont; font.pixelSize: 13; wrapMode: Text.Wrap }
                                    Label { Layout.fillWidth: true; text: neighborRow.modelData.scutCoverage && neighborRow.modelData.scutCoverage.covered ? "SCUT · " + neighborRow.modelData.scutCoverage.networkName : "OUTSIDE KNOWN SCUT"; color: neighborRow.modelData.scutCoverage && neighborRow.modelData.scutCoverage.covered ? Constants.nominalColor : Constants.warningColor; font.family: Constants.technicalFont; font.pixelSize: 12 }
                                }
                                Button { text: "USE FOR MANUAL TRAVEL"; onClicked: root.chooseSector(neighborRow.modelData) }
                                Button { text: "SCAN"; onClicked: root.scanRequested(neighborRow.modelData.x, neighborRow.modelData.y, neighborRow.modelData.z) }
                            }
                            MouseArea { id: neighborMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: transportReview
        anchors.centerIn: parent
        modal: true
        width: Math.min(root.width - 80, 780)
        title: "REVIEW ROUND-TRIP TRANSPORT"
        property var cycle: (root.selectedTransportCycle.metadata || {}).cycle || ({})
        ColumnLayout {
            width: parent.width; spacing: 12
            Label { Layout.fillWidth: true; text: String(transportReview.cycle.resourceType || "resource").replace("_", " ").toUpperCase() + " · " + (String(transportReview.cycle.loadSourceMode || "probe") === "mine_in_sector" ? "MINE IN SECTOR" : "LOAD FROM PROBE"); color: Constants.cyanColor; font.family: Constants.technicalFont; font.pixelSize: 17; font.bold: true; wrapMode: Text.Wrap }
            Label { Layout.fillWidth: true; text: "1 · TRAVEL TO " + root.coordinateLabel(transportReview.cycle.source); color: Constants.textColor; font.family: Constants.technicalFont; font.bold: true; wrapMode: Text.Wrap }
            Label { Layout.fillWidth: true; text: "2 · " + (String(transportReview.cycle.loadSourceMode || "probe") === "mine_in_sector" ? "MINE " + String(transportReview.cycle.resourceType || "resource").replace("_", " ").toUpperCase() : "LOAD FROM PROBE " + String(transportReview.cycle.sourceProbeId || "UNSELECTED")) + (transportReview.cycle.loadAmount !== null && transportReview.cycle.loadAmount !== undefined ? " UNTIL " + Number(transportReview.cycle.loadAmount) + " ECE" : " UNTIL " + Number(transportReview.cycle.loadUntilPercent || 0) + "% FULL"); color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
            Label { Layout.fillWidth: true; text: "3 · TRAVEL TO " + root.coordinateLabel(transportReview.cycle.destination) + " AND KEEP FILLING PROBE " + String(transportReview.cycle.destinationProbeId || "UNSELECTED") + " AS SPACE OPENS, UNTIL THE TANKER REACHES ITS PROTECTED RETURN RESERVE"; color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
            Label { Layout.fillWidth: true; text: "4 · RETURN TO " + root.coordinateLabel(transportReview.cycle.returnPoint) + (transportReview.cycle.repeat ? " AND REPEAT" : " AND COMPLETE"); color: Constants.textColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
            Label { Layout.fillWidth: true; text: "SAFETY · PROTECT " + Number(transportReview.cycle.protectedDeuterium || 0) + "% DEUTERIUM PLUS " + Number(transportReview.cycle.reserveHops || 0) + " RESERVE HOPS"; color: Constants.warningColor; font.family: Constants.technicalFont; wrapMode: Text.Wrap }
            RowLayout {
                Layout.fillWidth: true
                Button { text: "REMOVE ROUTE"; onClicked: { root.transportCycleDeleteRequested(String(root.selectedTransportCycle.id)); transportReview.close(); } }
                Item { Layout.fillWidth: true }
                Button { text: "CLOSE"; onClicked: transportReview.close() }
                Button { visible: String(root.selectedTransportCycle.state || "planned") === "active"; text: "PAUSE ACTIVE ROUTE"; onClicked: { root.transportCyclePauseRequested(String(root.selectedTransportCycle.id)); transportReview.close(); } }
                Button { visible: String(root.selectedTransportCycle.state || "planned") !== "active"; text: "CONFIRM & START"; onClicked: { root.transportCycleStartRequested(String(root.selectedTransportCycle.id)); transportReview.close(); } }
            }
        }
    }

}
