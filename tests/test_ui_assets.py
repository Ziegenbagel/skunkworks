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


def test_galaxy_map_uses_rotatable_three_dimensional_scene():
    workspace = Path("src/ui/qml/components/NavigationWorkspace.qml").read_text()
    galaxy = Path("src/ui/qml/components/GalaxyMap3D.qml").read_text()

    assert "GalaxyMap3D" in workspace
    assert "import QtQuick3D" in galaxy
    assert "View3D" in galaxy
    assert "OrbitCameraController" in galaxy
    assert "Repeater3D" in galaxy


def test_settings_exposes_policy_gated_automation_queue_and_approval():
    settings = Path("src/ui/qml/components/AutomationSettings.qml").read_text()
    app = Path("src/ui/qml/App.qml").read_text()

    assert "AUTOMATION EXECUTION" in settings
    assert "ALLOW SKUNKWORKS TO SEND GAME ORDERS" in settings
    assert "MAX ORDERS PER 60-SECOND CYCLE" in settings
    assert "COMMAND ALLOWLIST" in settings
    assert "PROPOSED COMMAND QUEUE" in settings
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
