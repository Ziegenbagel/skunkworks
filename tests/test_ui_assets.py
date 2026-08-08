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

    assert screen.count("SummaryListPanel") == 2
    assert "onClicked: details.open()" in panel
    assert "Dialog {" in panel
    assert "ScrollView" in panel


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
        "SAME-SECTOR PROBE TRANSFERS",
        "detach-storage-container",
        "drop-storage-container",
        "recover-storage-container",
        "transfer-deuterium-to-probe",
        "transfer-to-probe",
        '"salvage"',
        '"mine"',
        '"attach_to_probe"',
        "MANUAL MINING DESTINATION",
    ):
        assert control in workspace
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


def test_galaxy_map_uses_rotatable_three_dimensional_scene():
    workspace = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    galaxy = Path("src/ui/qml/components/GalaxyMap3D.qml").read_text()

    assert "GalaxyMap3D" in workspace
    assert "focusedProbeId: root.focusedProbeId" in workspace
    assert "function focusedNode()" in galaxy
    assert "CENTER PROBE" in galaxy
    assert "function panBy(" in galaxy
    assert "RIGHT/MIDDLE DRAG · PAN" in galaxy
    assert "import QtQuick3D" in galaxy
    assert "View3D" in galaxy
    assert "OrbitCameraController" in galaxy
    assert "Repeater3D" in galaxy
    assert "pickable: true" in galaxy
    assert "CLICK A SECTOR DOT FOR DETAILS" in galaxy
    assert "HAZARDS ONLY" in galaxy
    assert "CONFIRMED WITHOUT" in galaxy
    assert "ORGANIC / CARBON COMPOUNDS" in galaxy
    assert "DROPPED CONTAINERS" in galaxy
    assert "FOCUSED PROBE · RECENT 10 TRAIL" in galaxy
    assert "recentTrail" in galaxy
    assert "filtersExpanded" in galaxy
    assert "Collapse map filters" in galaxy
    assert "SCUT TRANSIT BEACONS" in Path("src/ui/qml/components/AutomationSettings.qml").read_text()


def test_navigation_exposes_all_neighbor_scan_and_explorer_arrival_automation():
    navigation = Path("src/ui/qml/components/NavigationControl.qml").read_text()
    controller = Path("src/ui/controller.py").read_text()
    assert "SCAN ALL 12 NEIGHBORING SECTORS" in navigation
    assert "neighborScanRequested" in navigation
    assert "scanNeighboringSectors" in controller
    assert "explorer_neighbor_scan" in controller


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
    assert "MAX ORDERS PER 60-SECOND CYCLE" in settings
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
    assert "GridLayout" in workspace
    assert "font.pixelSize: 15" in workspace
    assert "ResourceWorkspace" in navigation


def test_navigation_separates_manual_transport_and_scanning_workflows():
    navigation = Path("src/ui/qml/components/NavigationControl.qml").read_text()

    assert 'TabButton { text: "MANUAL TRAVEL" }' in navigation
    assert 'TabButton { text: "TRANSPORT AUTOMATION" }' in navigation
    assert 'TabButton { text: "SECTOR SCANNING" }' in navigation
    assert "LOADING SECTOR" in navigation
    assert "UNLOADING SECTOR" in navigation
    assert "RETURN POINT" in navigation
    assert "loadUntilPercent" in navigation
    assert "unloadUntilPercent" in navigation
    assert "protectedDeuterium" in navigation
    assert 'focusedRole === "transport"' in navigation


def test_inventory_workspace_exposes_identity_rules_items_and_transfers():
    inventory = Path("src/ui/qml/components/InventoryWorkspace.qml").read_text()
    resources = Path("src/ui/qml/components/ResourceWorkspace.qml").read_text()
    fleet = Path("src/ui/qml/components/FleetWorkspace.qml").read_text()

    assert "RENAME FOCUSED PROBE" in fleet
    assert "RENAME" in inventory
    assert "PREFERRED CONTENTS" in inventory
    assert "ANY CONTENTS" in inventory
    assert "MOVE STOCK BETWEEN CONTAINERS" in inventory
    assert "STORED ITEMS & EQUIPMENT" in inventory
    assert "CONFIRM STORAGE TRANSFER" in inventory
    assert "INVENTORY & CONTAINERS" in resources
    assert "replaceAll(" not in inventory


def test_fleet_workspace_exposes_quick_manual_mining_orders():
    fleet = Path("src/ui/qml/components/FleetWorkspace.qml").read_text()
    navigation = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    manual = Path("src/ui/qml/components/ManualControlWorkspace.qml").read_text()
    app = Path("src/ui/qml/App.qml").read_text()

    assert "MANUAL MINING ORDER" in fleet
    assert "REVIEW MINING ORDER" in fleet
    assert "maximumMiningOrderAmount" in fleet
    assert '"targetAmount"' in fleet
    assert "manualMiningRequested" in navigation
    assert "inventoryManagement || {}).miningTargets" in manual
    assert 'runInventoryMannyAction("mine", mannyId, payload)' in app


def test_logbook_workspace_uses_editable_game_pages_and_opt_in_reports():
    logbook = Path("src/ui/qml/components/LogbookWorkspace.qml").read_text()
    app = Path("src/ui/qml/App.qml").read_text()

    assert "FLEET LOGBOOK PAGES" in logbook
    assert "+ NEW PAGE" in logbook
    assert "SAVE CHANGES" in logbook
    assert "DELETE LOGBOOK PAGE?" in logbook
    assert "AUTO-LOG MAJOR SKUNKWORKS REPORTS & DISCOVERIES" in logbook
    assert "loadLogbookPage" in app


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
