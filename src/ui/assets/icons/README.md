# Skunkworks Icon Assets

These production PNGs were generated with the built-in image-generation tool
from the player-provided Skunkworks dashboard and icon-concept references, then
processed locally from a flat magenta chroma background into transparent PNGs.

## Deliverables

- The application identity mark: a white Copperplate Bold `S` on black,
  exported as a 1024px PNG, a multi-resolution Windows ICO, and a macOS ICNS.
  It is generated deterministically by `tools/generate_app_icon.py`.
- Fourteen 512×512 map/entity icons: probe, hub, Manny, SCUT relay, habitable
  world, wandering asteroid, resource asteroid, black hole, quest,
  civilization, anomaly, deuterium station, storage container, and mining site.
- Twelve 512×512 status/utility icons: online, offline, warning, critical,
  success, fuel, power, shield, research, communication, settings, and info.
- Transparent master atlases and chroma-key source atlases for future controlled
  re-exporting.

## Map expansion

The API-parity expansion adds twenty 512×512 RGBA assets:

- Deuterium tanker probe, live star, stellar remnant, solar system, and dust cloud.
- Rocky, frozen, ocean, lava, dwarf, gas-giant, and ice-giant planets.
- Drifting item, detached container, dormant construct, unknown contact, and
  waypoint bookmark.
- SCUT transit-beacon, hidden-container, and salvageable-object overlay badges.

An additional twenty-icon semantic badge atlas supplies active/degraded/offline
relay states, planet-dropped containers, abandoned Mannys, mining and selection
targets, ownership and scan confidence, four resource types plus depletion, and
all five asteroid-composition classes. Medium scan confidence is represented by
the high-confidence badge at reduced opacity, avoiding a redundant raster.

`map-icons-expansion-master-chroma.png` is the generated 5×4 source atlas and
`map-icons-expansion-master.png` is its transparent master. Run
`tools/ui/slice_icon_atlas.py` after intentionally replacing the master to
rebuild the individual files. The equivalent badge sources are
`map-badges-master-chroma.png` and `map-badges-master.png`. `AssetCatalog.qml` is the canonical runtime
mapping from API object types and probe models to these assets.

SCUT connections are intentionally not raster assets. `ScutNetworkOverlay.qml`
draws outlined, dashed paths only between relay nodes whose transit beacons are
installed, allowing paths to follow live galaxy coordinates and state.

All individual files use transparent RGBA backgrounds and generous square
padding so QML can scale them consistently on galaxy maps, sector maps, cards,
and status controls.

## Generation Prompt Summary

The primary atlas requested an original cohesive 7×2 family of premium 2D
aerospace map icons with white-silver technical linework, cyan highlights,
restrained semantic colors, consistent line weight, no text, and isolated
subjects. The utility atlas requested an original 6×2 family using the same
finish for twelve explicit operational-status symbols. Both used a uniform
`#ff00ff` removable background; the final images were despilled and converted
to alpha transparency.
