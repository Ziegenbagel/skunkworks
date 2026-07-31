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
