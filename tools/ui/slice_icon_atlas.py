"""Slice the fixed Skunkworks expansion atlas into square RGBA map assets."""

from pathlib import Path

from PIL import Image


EXPANSION_ICON_NAMES = (
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

MAP_BADGE_NAMES = (
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


def slice_atlas(source: Image.Image, icon_dir: Path, names: tuple[str, ...]) -> None:
    columns, rows = 5, 4

    for index, name in enumerate(names):
        column, row = index % columns, index // columns
        left = round(column * source.width / columns)
        right = round((column + 1) * source.width / columns)
        top = round(row * source.height / rows)
        bottom = round((row + 1) * source.height / rows)
        cell = source.crop((left, top, right, bottom))

        side = max(cell.size)
        square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        square.alpha_composite(
            cell,
            ((side - cell.width) // 2, (side - cell.height) // 2),
        )
        square.resize((512, 512), Image.Resampling.LANCZOS).save(
            icon_dir / f"{name}.png",
            optimize=True,
        )


def main() -> None:
    icon_dir = Path(__file__).resolve().parents[2] / "src/ui/assets/icons"
    atlases = (
        ("map-icons-expansion-master.png", EXPANSION_ICON_NAMES),
        ("map-badges-master.png", MAP_BADGE_NAMES),
    )
    for filename, names in atlases:
        source = Image.open(icon_dir / filename).convert("RGBA")
        slice_atlas(source, icon_dir, names)


if __name__ == "__main__":
    main()
