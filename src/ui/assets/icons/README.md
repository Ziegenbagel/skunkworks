# Skunkworks Icon Assets

These production PNGs were generated with the built-in image-generation tool
from the player-provided Skunkworks dashboard and icon-concept references, then
processed locally from a flat magenta chroma background into transparent PNGs.

## Deliverables

- Fourteen 512×512 map/entity icons: probe, hub, Manny, SCUT relay, habitable
  world, wandering asteroid, resource asteroid, black hole, quest,
  civilization, anomaly, deuterium station, storage container, and mining site.
- Twelve 512×512 status/utility icons: online, offline, warning, critical,
  success, fuel, power, shield, research, communication, settings, and info.
- Transparent master atlases and chroma-key source atlases for future controlled
  re-exporting.

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
