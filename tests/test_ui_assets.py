from pathlib import Path

from PIL import Image


ICON_ROOT = Path("src/ui/assets/icons")
EXPANSION_ICONS = (
    "probe-tanker",
    "star",
    "star-remnant",
    "solar-system",
    "dust-cloud",
    "planet-rocky",
    "planet-frozen",
    "planet-ocean",
    "planet-lava",
    "planet-dwarf",
    "planet-gas-giant",
    "planet-ice-giant",
    "drifting-item",
    "detached-container",
    "dormant-construct",
    "unknown-object",
    "waypoint-bookmark",
    "badge-scut-transit-beacon",
    "badge-hidden-container",
    "badge-salvageable",
)

MAP_BADGES = (
    "badge-relay-active",
    "badge-relay-degraded",
    "badge-relay-offline",
    "badge-container-on-planet",
    "badge-manny-abandoned",
    "badge-mining-target",
    "badge-selected-object",
    "badge-unknown-ownership",
    "badge-scan-low",
    "badge-scan-high",
    "badge-resource-deuterium",
    "badge-resource-metals",
    "badge-resource-ice",
    "badge-resource-carbon-compounds",
    "badge-resource-depleted",
    "badge-composition-iron",
    "badge-composition-silicate",
    "badge-composition-carbonaceous",
    "badge-composition-ice",
    "badge-composition-rare-metals",
)


def test_expansion_icons_are_square_transparent_production_pngs():
    for name in EXPANSION_ICONS + MAP_BADGES:
        image = Image.open(ICON_ROOT / f"{name}.png")
        assert image.size == (512, 512)
        assert image.mode == "RGBA"
        assert image.getchannel("A").getextrema() == (0, 255)


def test_asset_catalog_covers_current_api_objects_and_tanker():
    catalog = Path("src/ui/qml/AssetCatalog.qml").read_text()
    for object_type in (
        "star",
        "planet",
        "asteroid",
        "dust_cloud",
        "black_hole",
        "solar_system",
        "manny",
        "drifting_item",
        "detached_container",
        "deuterium_refuel_station",
        "dormant_construct",
        "scut_relay",
        "deuterium_tanker",
    ):
        assert f'"{object_type}"' in catalog


def test_dashboard_keeps_persistent_probe_selector_binding_seam():
    screen = Path("src/ui/qml/MissionControlScreen.ui.qml").read_text()
    selector = Path("src/ui/qml/components/ProbeSelector.qml").read_text()

    assert "property alias probeSelectorControl" in screen
    assert "ProbeSelector" in screen
    assert "signal probeSelected(int probeId)" in selector
    assert "signal refreshRequested" in selector
    assert '"deuterium_tanker"' in screen


def test_summary_panels_open_full_detail_dialogs_without_dashboard_scrollbars():
    screen = Path("src/ui/qml/MissionControlScreen.ui.qml").read_text()
    panel = Path("src/ui/qml/components/SummaryListPanel.qml").read_text()

    assert screen.count("SummaryListPanel") == 1
    assert "Focused Probe Hull Integrity" in screen
    assert "onClicked: details.open()" in panel
    assert "Dialog {" in panel
    assert "ScrollView" in panel
    assert "previewFontSize: 13" in screen
    assert "summaryFontSize: 11" in screen


def test_dashboard_branding_and_footer_use_readable_current_product_labels():
    screen = Path("src/ui/qml/MissionControlScreen.ui.qml").read_text()

    assert "id: brandLine" in screen
    assert "Math.round(30 * root.uiScale)" in screen
    assert "SKUNKWORKS UI CONCEPT" not in screen
    assert "SKUNKWORKS MISSION CONTROL" in screen
    assert "GAME API v" in screen
    assert "GAME API VERSION PENDING" in screen
    assert 'font.pixelSize: Math.round(12 * root.uiScale)' in screen


def test_top_navigation_is_interactive_and_has_connected_workspace():
    screen = Path("src/ui/qml/MissionControlScreen.ui.qml").read_text()
    navigation = Path("src/ui/qml/components/TopNavigationBar.qml").read_text()

    assert "TopNavigationBar" in screen
    assert "NavigationWorkspace" in screen
    assert "signal sectionSelected(string section)" in navigation
    assert "onClicked: root.sectionSelected" in navigation
    assert '"RESEARCH"' not in navigation
    assert "Math.min(18, Math.max(13, root.width / 125))" in navigation


def test_fleet_workspace_exposes_live_probe_upgrade_controls():
    fleet = Path("src/ui/qml/components/FleetWorkspace.qml").read_text()
    workspace = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    manual = Path("src/ui/qml/components/ManualControlWorkspace.qml").read_text()
    app = Path("src/ui/qml/App.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()

    assert "MANUAL PROBE UPGRADE" in fleet
    assert "INSTALL UPGRADE" in fleet
    assert "upgradeRequested" in fleet
    assert "ManualControlWorkspace" in workspace
    assert "probeImprovements" in manual
    assert "onManualUpgradeRequested" in app
    assert "def queueManualUpgrade" in controller


def test_manual_crafting_exposes_recipe_and_probe_assembly_references():
    manual = Path("src/ui/qml/components/ManualControlWorkspace.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()
    assembly = Path("src/planner/assembly.py").read_text()
    assert "CRAFTING REFERENCE · ALL AVAILABLE RECIPES" in manual
    assert "TOTAL RAW RESOURCES" in manual
    assert "rawIngredients" in manual
    assert "PROBE ASSEMBLY REQUIREMENTS" in manual
    assert '"probeAssemblies"' in controller
    assert "PROBE_ASSEMBLY_REQUIREMENTS" in assembly
    assert "GENERIC_COMPONENTS" in assembly
    assert '"Generic Class Probe"' in controller
    assert '"Tanker Class Probe"' in controller
    assert "MANUAL PROBE ASSEMBLY" in manual
    assert "REVIEW PROBE ASSEMBLY" in manual
    assert "consumes the selected assembly Manny" in manual
    assert "installed aboard the newly assembled probe" in manual
    assert "queueManualProbeAssembly" in controller


def test_galaxy_map_operational_colors_override_trail_and_resources():
    galaxy = Path("src/ui/qml/components/GalaxyMap3D.qml").read_text()
    hazard = galaxy.index('if (node.hasHazard) return "#ff4d5a";')
    current = galaxy.index('if (String(node.mapState || "unknown") === "current"')
    trail = galaxy.index("if (showRecentTrail && recentTrailNodes")
    resources = galaxy.index("const selected = selectedResources();", trail)

    assert hazard < current < trail < resources
    assert '{"label":"HAZARD", "color":"#ff4d5a"}' in galaxy


def test_remaining_v107_controls_are_exposed_in_their_safe_workspaces():
    fleet = Path("src/ui/qml/components/FleetWorkspace.qml").read_text()
    safety = Path("src/ui/qml/components/SafetyWorkspace.qml").read_text()
    navigation = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()
    assert "MAKE DEFAULT" in fleet
    assert "makeFocusedProbeDefault" in controller
    assert "TERMINAL PROBE RECOVERY" in safety
    assert "REVIEW MIND-SNAPSHOT REASSIGNMENT" in safety
    assert "reassignMindSnapshot" in controller
    assert 'root.section === "SAFETY"' in navigation


def test_automation_queue_names_the_actual_output_for_each_craft():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()

    assert "outputLabel" in settings
    assert '"outputLabel"' in controller


def test_inventory_workspace_exposes_complete_manual_game_controls():
    workspace = Path("src/ui/qml/components/InventoryWorkspace.qml").read_text()
    for control in (
        "MANUAL JETTISON & ITEM HANDOFF",
        "CONTAINER DEPLOYMENT, RECOVERY & PROBE HANDOFF",
        "detach-storage-container",
        "drop-storage-container",
        "recover-storage-container",
        '"salvage"',
        '"attach_to_probe"',
        "SCUT RELAY DEPLOYMENT & SECTOR OPERATIONS",
        '"turn-on-relay"',
        '"install-scut-transit-beacon"',
        '"inspect-sector-object"',
        '"install-bookmark"',
        '"refill-deuterium-tank"',
        '"drop-manny-cargo"',
    ):
        assert control in workspace
    assert "MANUAL MINING DESTINATION" not in workspace
    assert "SAME-SECTOR PROBE TRANSFERS" not in workspace
    assert "CONFIRM LIVE INVENTORY ORDER" in workspace


def test_settings_exposes_official_update_channel():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()
    assert "CHECK FOR UPDATES" in settings
    assert "updateCheckRequested" in settings
    assert "https://github.com/Ziegenbagel/skunkworks/releases/latest" in controller


def test_settings_numeric_targets_accept_keyboard_entry():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    for control_id in (
        "genericTarget", "tankerTarget", "mannyTarget", "containerTarget",
        "relayTarget", "beaconTarget", "deuteriumReserve", "metalsReserve",
        "iceReserve", "carbonReserve",
    ):
        declaration = settings.split("id: " + control_id, 1)[1].split("}", 1)[0]
        assert "editable: true" in declaration
    assert "valueFromText: function(text, locale)" in settings


def test_settings_exposes_privacy_safe_diagnostic_logs():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()
    diagnostics = Path("src/diagnostics.py").read_text()
    assert "OPEN DIAGNOSTIC LOGS" in settings
    assert "openDiagnosticLogs" in controller
    assert "RotatingFileHandler" in diagnostics
    assert "[REDACTED]" in diagnostics


def test_dashboard_density_controls_scale_summaries_and_bound_sector_labels():
    screen = Path("src/ui/qml/MissionControlScreen.ui.qml").read_text()
    telemetry = Path("src/ui/qml/components/TelemetryBar.qml").read_text()
    sector = Path("src/ui/qml/components/SectorView.qml").read_text()
    assert "font.pixelSize: 34" in screen
    assert "height: 14" in telemetry
    assert "maximumFreeObjects: 8" in sector
    assert "MORE SECTOR OBJECTS" in sector
    assert "readonly property bool above" in sector


def test_hull_panel_uses_release_thresholds_without_duplicate_reading():
    screen = Path("src/ui/qml/MissionControlScreen.ui.qml").read_text()
    telemetry = Path("src/ui/qml/components/TelemetryBar.qml").read_text()
    assert "focusedHullPercent <= 10" in screen
    assert "focusedHullPercent <= 25" in screen
    assert "showReading: false" in screen
    assert "property bool showReading: true" in telemetry


def test_galaxy_map_uses_rotatable_three_dimensional_scene():
    workspace = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    galaxy = Path("src/ui/qml/components/GalaxyMap3D.qml").read_text()

    assert "GalaxyMap3D" in workspace
    assert "focusedProbeId: root.focusedProbeId" in workspace
    assert "function focusedNode()" in galaxy
    assert "nodeIndex[coordinateId]" in galaxy
    assert "probeIds.indexOf(focusedProbeId)" not in galaxy
    assert "CENTER PROBE" in galaxy
    assert "function panBy(" in galaxy
    assert "RIGHT/MIDDLE DRAG · PAN" in galaxy
    assert "import QtQuick3D" in galaxy
    assert "View3D" in galaxy
    assert "mapFrom3DScene" in galaxy
    assert '\"label\": \"0, 0, 0\"' not in galaxy
    assert '\"label\": \"X\"' in galaxy
    assert '\"label\": \"Y\"' in galaxy
    assert '\"label\": \"Z\"' in galaxy
    assert "SHOW X / Y / Z AXIS LABELS" in galaxy
    assert "OrbitCameraController" in galaxy
    assert "Repeater3D" in galaxy
    assert "pickable: true" in galaxy
    assert "CLICK A SECTOR DOT FOR DETAILS" in galaxy
    assert 'objectName: "scut:"' in galaxy
    assert "SCUT BOUNDARY · FCC" in galaxy
    assert "selectedCoveragePoint" in galaxy
    assert "HAZARDS ONLY" in galaxy
    assert "HAS ANY SELECTED RESOURCE" in galaxy
    assert 'CheckBox { text: "DEUTERIUM"' in galaxy
    assert 'CheckBox { text: "METALS"' in galaxy
    assert 'CheckBox { text: "ICE"' in galaxy
    assert 'CheckBox { text: "ORGANIC / CARBON COMPOUNDS"' in galaxy
    assert "ORGANIC / CARBON COMPOUNDS" in galaxy
    assert "function isGodSector(" in galaxy
    assert "ALL FOUR RESOURCES · GOD SECTOR · GOLD" in galaxy
    assert '"label":"GOD SECTOR", "color":"#ffd34d"' in galaxy
    assert "id: godSectorHalo" in galaxy
    assert "pickable: false" in galaxy
    assert "DROPPED CONTAINERS" in galaxy
    assert "FOCUSED PROBE · RECENT 10 TRAIL" in galaxy
    assert "recentTrail" in galaxy
    assert "filtersExpanded" in galaxy
    assert "Collapse map filters" in galaxy
    assert "id: filterScroll" in galaxy
    assert "visible: root.showAxisLabels" in galaxy
    assert 'text: "SCANNED"' in galaxy
    assert 'text: "OBSERVED"' not in galaxy
    assert 'text: "UNKNOWN"' not in galaxy


def test_probe_selector_display_is_keyed_to_authoritative_focus_id():
    selector = Path("src/ui/qml/components/ProbeSelector.qml").read_text()

    assert "readonly property var selectedProbe: probeForId(currentProbeId)" in selector
    assert "text: root.selectedProbe ? String(root.selectedProbe.name" in selector


def test_transit_panel_labels_failed_refresh_data_as_last_known():
    sector = Path("src/ui/qml/components/SectorView.qml").read_text()
    screen = Path("src/ui/qml/MissionControlScreen.ui.qml").read_text()

    assert "LAST KNOWN TRAVEL TELEMETRY" in sector
    assert 'connectionState: String(root.dashboardData.connection' in screen
    assert "SCUT TRANSIT BEACONS" in Path("src/ui/qml/components/AutomationSettings.qml").read_text()


def test_navigation_exposes_all_neighbor_scan_and_explorer_arrival_automation():
    navigation = Path("src/ui/qml/components/NavigationControl.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()
    assert "SCAN ALL 12 NEIGHBORING SECTORS" in navigation
    assert "neighborScanRequested" in navigation
    assert "scanNeighboringSectors" in controller
    assert "explorer_neighbor_scan" in controller
    assert "CURRENT SECTOR" in navigation
    assert "No detailed system telemetry is available for the current sector." in navigation


def test_sector_view_uses_one_orbit_per_planet_and_readable_markers():
    sector = Path("src/ui/qml/components/SectorView.qml").read_text()
    assert 'String(item.type).toLowerCase() === "planet"' in sector
    assert "ONE ORBIT PER PLANET" in sector
    assert "width: 80; height: 80" in sector
    assert "context.ellipse(root.centerX - horizontalRadius" in sector
    assert "root.centerY - verticalRadius" in sector
    assert "horizontalRadius * 2" in sector
    assert "verticalRadius * 2" in sector
    assert "maximumMannyAreas: 12" in sector
    assert "buildMannyClusters" in sector
    assert "freeObjectIndex(modelData.targetObjectId)" in sector
    assert "const edgeBuffer = 46" in sector
    assert "leftRows" in sector and "rightRows" in sector
    assert "relayObjects" in sector
    assert "SCUT RELAY · TRANSIT BEACON" in sector
    assert "irregularAngles" in sector
    assert "freeTargetIndex % 2" in sector


def test_app_uses_a_dedicated_live_data_loading_screen():
    app = Path("src/ui/qml/App.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()
    assert "startupOverlay" in app
    assert "LOADING LIVE FLEET DATA" in app
    assert "window.backend.startupLoading" in app
    assert "def startupLoading" in controller
    assert "loadingProgress" in app
    assert "loadingStatus" in app


def test_live_failures_never_substitute_concept_dashboard_data():
    app = Path("src/ui/qml/App.qml").read_text()
    screen = Path("src/ui/qml/MissionControlScreen.ui.qml").read_text()
    assert "LIVE FLEET DATA UNAVAILABLE" in app
    assert "SHOWING LAST SUCCESSFUL SNAPSHOT" in app
    assert "availableProbes: window.backend ? window.backend.availableProbes : previewProbes" in app
    assert "liveMode ? []" in screen


def test_probe_selector_waits_for_backend_confirmation():
    selector = Path("src/ui/qml/components/ProbeSelector.qml").read_text()
    assert "Number(currentValue)" in selector
    assert "root.probeSelected(requestedProbeId)" in selector
    assert "currentIndex = root.indexForProbe(root.currentProbeId)" in selector


def test_audio_manager_bundles_selected_v1_assets_and_controls():
    audio = Path("src/ui/qml/components/AudioManager.qml").read_text()
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    assert Path("src/ui/assets/audio/music/space-ambient-cinematic-music.mp3").stat().st_size > 1_000_000
    assert Path("src/ui/assets/audio/sfx/button/soft-ui-button-click.ogg").is_file()
    assert Path("src/ui/assets/audio/sfx/chimey/Chime_Confirm.mp3").is_file()
    assert Path("src/ui/assets/audio/sfx/alerts/Wrong Error.wav").is_file()
    assert "loops: MediaPlayer.Infinite" in audio
    assert '"press": "../../assets/audio/sfx/button/soft-ui-button-click.ogg"' in audio
    assert "id: effectPlayer" in audio
    assert "function hover()" in audio
    assert '"confirm": "../../assets/audio/sfx/chimey/Chime_Confirm.mp3"' in audio
    assert 'category: "audio"' in audio
    assert 'title: "AUDIO"' in settings
    assert "MUSIC VOLUME" in settings
    assert "EFFECTS VOLUME" in settings
    assert Path("src/ui/assets/audio/AUDIO_LICENSES.md").is_file()


def test_settings_exposes_policy_gated_automation_queue_and_approval():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    app = Path("src/ui/qml/App.qml").read_text()

    assert "AUTOMATION EXECUTION" in settings
    assert "ALLOW SKUNKWORKS TO SEND GAME ORDERS" in settings
    assert "MAX ORDERS PER 1-MINUTE CYCLE" in settings
    assert "COMMAND ALLOWLIST" in settings
    assert "PROPOSED COMMAND QUEUE" in settings
    assert "function hasUnblockedCommand()" in settings
    assert "WHY HIGHER-PRIORITY ORDERS ARE WAITING" in settings
    assert "automationApprovalRequested" in settings
    assert "saveExecutionPolicy" in app
    assert "runAutomationCycle" in app


def test_resource_workspace_groups_locations_and_uses_responsive_cards():
    workspace = Path("src/ui/qml/components/ResourceWorkspace.qml").read_text()
    navigation = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()

    for heading in (
        "PROBE STORAGE", "DRIFTING CONTAINERS", "PLACED CONTAINERS",
        "ASTEROID CONTENTS", "PLANETARY RESOURCES",
    ):
        assert heading in workspace
    assert "Grid {" in workspace
    assert "font.pixelSize: 15" in workspace
    assert "ResourceWorkspace" in navigation


def test_navigation_moves_transport_workflow_to_probe_role_settings():
    navigation = Path("src/ui/qml/components/NavigationControl.qml").read_text()
    role_settings = Path("src/ui/qml/components/ProbeRoleSettings.qml").read_text()

    assert 'TabButton { text: "MANUAL TRAVEL" }' in navigation
    assert 'root.roleSettingsOnly ? 1' in navigation
    assert 'TabButton { text: "SECTOR SCANNING" }' in navigation
    assert "roleSettingsOnly: true" in role_settings
    assert "RESERVE TANKER REFILL CHAIN" in role_settings
    assert "targetProbeId" in role_settings
    assert "TabBar" not in role_settings
    assert "visible: root.canManageRoles" in role_settings
    assert "contentWidth: availableWidth" in role_settings
    assert "roleScroll.availableWidth" in role_settings
    assert "anchors.centerIn: parent" in role_settings
    assert "LOADING SECTOR" in navigation
    assert "UNLOADING SECTOR" in navigation
    assert "RETURN POINT" in navigation
    assert "loadUntilPercent" in navigation
    assert "unloadUntilPercent" in navigation
    assert "protectedDeuterium" in navigation
    assert 'focusedRole === "transport"' in navigation
    assert "SAVE AUTO-TRAVEL DESTINATION" in navigation
    assert "ACTIVE AUTO-TRAVEL TARGET" in navigation
    assert "CANCEL AUTO-TRAVEL TARGET" in navigation
    assert "scanSummary" in navigation
    assert "transportAutomationScroll.availableWidth" in navigation
    assert "contentHeight: root.transportContentExtent" in navigation
    assert "transportAutomationContent.childrenRect.height" in navigation
    assert 'property: "interactive"' in navigation
    assert "? ScrollBar.AlwaysOff : ScrollBar.AsNeeded" in navigation
    assert "contentHeight: roleSettingsContent.implicitHeight" in role_settings
    assert "transportRoleControl.transportContentExtent" in role_settings
    assert "ScrollBar.vertical.policy: ScrollBar.AlwaysOn" in role_settings
    assert navigation.index("Repeater {\n                        model: root.automationData.transportCycles") < navigation.index("Saved cycles are durable planned Operations")
    assert "width: Math.max(1, transportAutomationScroll.availableWidth); spacing: 10" in navigation
    assert "Layout.preferredHeight: 730" not in role_settings
    assert 'TabButton { text: "TRANSPORT AUTOMATION"' not in navigation


def test_transit_panels_render_full_auto_travel_itinerary():
    sector = Path("src/ui/qml/components/SectorView.qml").read_text()
    fleet = Path("src/ui/qml/components/FleetWorkspace.qml").read_text()

    assert 'journeyLabel || "AUTO-TRAVEL"' in sector
    assert "itineraryLabel" in sector
    assert "ITINERARY ·" in fleet


def test_settings_exposes_safe_application_shutdown():
    app = Path("src/ui/qml/App.qml").read_text()
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()

    assert "SHUTDOWN SKUNKWORKS" in settings
    assert "backend.shutdown()" in app
    assert "SHUTTING DOWN SAFELY" in app
    assert "onClosing" in app


def test_inventory_workspace_exposes_identity_rules_items_and_transfers():
    inventory = Path("src/ui/qml/components/InventoryWorkspace.qml").read_text()
    resources = Path("src/ui/qml/components/ResourceWorkspace.qml").read_text()
    manual = Path("src/ui/qml/components/ManualControlWorkspace.qml").read_text()
    navigation = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    fleet = Path("src/ui/qml/components/FleetWorkspace.qml").read_text()

    assert "RENAME FOCUSED PROBE" in fleet
    assert "RENAME" in inventory
    assert "PREFERRED CONTENTS" in inventory
    assert "ANY CONTENTS" in inventory
    assert "MOVE STOCK BETWEEN CONTAINERS" in inventory
    assert "STORED ITEMS & EQUIPMENT" in inventory
    assert "CONFIRM STORAGE TRANSFER" in inventory
    assert "InventoryWorkspace" not in resources
    assert "TabBar" not in resources
    assert "inventoryData" not in resources
    assert "TRANSFERS AND CONTAINERS" in manual
    assert "InventoryWorkspace" in manual
    assert "onStorageRulesSaveRequested" in navigation
    assert "onCraftingReservationsReassignRequested" in navigation
    assert "onStorageMoveRequested" in navigation
    assert "onJettisonRequested" in navigation
    assert "replaceAll(" not in inventory


def test_fleet_workspace_scopes_manny_auto_naming_to_focused_probe():
    fleet = Path("src/ui/qml/components/FleetWorkspace.qml").read_text()
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()

    assert "RENAME MANNY" in fleet
    assert "MANNY AUTO-NAMING · FOCUSED PROBE" in fleet
    assert "AUTO-NAME NEW MANNYS" in fleet
    assert "APPLY TO EXISTING MANNYS" in fleet
    assert "INFER FROM DEFAULT PROBE" not in fleet
    assert "PROBE TEMPLATE" not in fleet
    assert "{number:02d} gives 01, 02, 03" in fleet
    assert "id: fleetPageScroll" in fleet
    assert "width: Math.max(1, fleetPageScroll.availableWidth)" in fleet
    assert "id: fleetScroll" not in fleet
    assert "MANNY AUTO-NAMING" not in settings


def test_production_workspace_offers_name_task_and_state_sorting():
    navigation = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()

    assert 'property string productionSort: "name"' in navigation
    assert '"text": "NAME", "value": "name"' in navigation
    assert '"text": "TASK", "value": "task"' in navigation
    assert '"text": "STATE", "value": "state"' in navigation
    assert "function productionTaskLabel(taskType)" in navigation
    assert 'left.state === "active"' in navigation


def test_safety_workspace_wraps_large_alerts_in_a_full_page_scroll():
    safety = Path("src/ui/qml/components/SafetyWorkspace.qml").read_text()

    assert "id: safetyPageScroll" in safety
    assert "anchors.fill: parent" in safety
    assert "ScrollBar.horizontal.policy: ScrollBar.AlwaysOff" in safety
    assert "Layout.preferredHeight: alertDetails.implicitHeight + 36" in safety
    assert "Text.WrapAtWordBoundaryOrAnywhere" in safety
    assert "font.pixelSize: 17" in safety
    assert "font.pixelSize: 16" in safety


def test_fleet_workspace_exposes_quick_manual_mining_orders():
    fleet = Path("src/ui/qml/components/FleetWorkspace.qml").read_text()
    navigation = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    manual = Path("src/ui/qml/components/ManualControlWorkspace.qml").read_text()
    app = Path("src/ui/qml/App.qml").read_text()

    assert "MANUAL MINING ORDER" in fleet
    assert "REVIEW MINING ORDER" in fleet
    assert "maximumMiningOrderAmount" in fleet
    assert '"targetAmount"' in fleet
    assert 'String(miningResource.currentText) === "deuterium"' in fleet
    assert 'String(miningResource.currentText) === "deuterium"' in fleet
    assert "SAME-SECTOR PROBE TRANSFERS" in fleet
    assert '"transfer-deuterium-to-probe"' in fleet
    assert '"transfer-to-probe"' in fleet
    assert "TRANSFERS AND CONTAINERS" in manual
    assert "MINING AND MAINTENANCE" in manual
    assert "MINING_MAINTENANCE" not in manual
    assert "TRANSFERS_CONTAINERS" not in manual
    assert "manualMiningRequested" in navigation
    assert "inventoryManagement || {}).miningTargets" in manual
    assert 'runInventoryMannyAction("mine", mannyId, payload)' in app


def test_automation_tabs_avoid_qt_mnemonic_underscores_and_show_all_live_targets():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    manual = Path("src/ui/qml/components/ManualControlWorkspace.qml").read_text()

    assert 'TabButton { text: "GENERAL AUTOMATION" }' in settings
    assert 'TabButton { text: "MINING AND MAINTENANCE" }' in manual
    assert 'TabButton { text: "TRANSFERS AND CONTAINERS" }' in manual
    assert 'TabButton { text: "GENERAL & AUTOMATION" }' not in settings
    floors = settings.index('title: "RESOURCE & SAFETY FLOORS"')
    save = settings.index('text: "SAVE AUTOMATION TARGETS"')
    live = settings.index('title: "LIVE TARGET STATUS"')
    assert floors < save < live
    assert "settingsData.liveTargetStatus" in settings
    assert "settingsData.fleetStatus" not in settings


def test_automation_target_panels_share_quantity_and_priority_columns():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()

    assert settings.count("columns: 3; uniformCellWidths: true") == 2
    assert "targetNameColumnWidth" not in settings
    assert "targetQuantityColumnWidth" not in settings


def test_logbook_workspace_uses_editable_game_pages_and_opt_in_reports():
    logbook = Path("src/ui/qml/components/LogbookWorkspace.qml").read_text()
    app = Path("src/ui/qml/App.qml").read_text()

    assert "FOCUSED PROBE LOGBOOK" in logbook
    assert "+ NEW PAGE" in logbook
    assert "SAVE CHANGES" in logbook
    assert "DELETE LOGBOOK PAGE?" in logbook
    assert "AUTO-LOG DAILY ROLE REPORTS & MAJOR DISCOVERIES" in logbook
    assert "id: contentScroller" in logbook
    assert "ScrollBar.vertical.policy: ScrollBar.AsNeeded" in logbook
    assert "newDailyReportCount" in Path("src/ui/qml/components/CommunicationsWorkspace.qml").read_text()
    assert "newDailyReportCount" in Path("src/ui/qml/components/TopNavigationBar.qml").read_text()
    assert "loadLogbookPage" in app
    controller = Path("src/ui/controller.py").read_text()
    mutation = controller.split("def _logbook_mutation", 1)[1].split("@Slot(bool)", 1)[0]
    assert "_start_refresh" not in mutation


def test_settings_exposes_operator_manual_and_change_log_links():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    workspace = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    app = Path("src/ui/qml/App.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()
    assert "HELP & DOCUMENTATION" in settings
    assert "OPEN OPERATOR MANUAL" in settings
    assert "OPEN CHANGE LOG" in settings
    assert "operatorManualRequested" in workspace
    assert "onOperatorManualRequested" in app
    assert "def openOperatorManual" in controller
    assert "def openChangeLog" in controller


def test_live_section_grid_uses_stable_scroll_view_width():
    """Wrapped task cards must not feed their measured size back into the grid."""
    workspace = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()

    assert "width: sectionScroll.availableWidth" in workspace
    assert "Grid {\n                    id: sectionGrid" in workspace
    assert "GridLayout {\n                    id: sectionGrid" not in workspace
    assert "Layout.preferredWidth: (root.width" not in workspace


def test_resource_ledger_avoids_content_dependent_quick_layouts():
    workspace = Path("src/ui/qml/components/ResourceWorkspace.qml").read_text()

    assert "width: resourceScroll.availableWidth" in workspace
    assert "GridLayout {\n                        id: resourceGrid" not in workspace
    assert "ColumnLayout {\n                    width: root.width - 20" not in workspace
