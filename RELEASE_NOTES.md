# Skunkworks 1.0.8

Skunkworks 1.0.8 reviews Von Neumann Game API v126–v128. Live Sector now uses
the v128 autonomous-unit observation endpoint to show locally deployed Mannys
and Others auxiliaries with their carrier and spatial state.

Remote laser targeting of an owned Manny is presented as a critical Safety
alert with its ten-minute destruction countdown, relative FCC sector, and a
direct route to Galaxy Map. Combat Control adds a per-probe opt-in that
revalidates the live alert and owned Manny identity before issuing exactly one
recall. It never moves the carrier probe, chooses a target, or acts on an
ambiguous alert, and the emergency stop disables it.

## Skunkworks 1.0.7

Skunkworks 1.0.7 reviews and integrates Von Neumann Game API v123–v125. Probe
missile launches now use the canonical Manny-scoped `ignite_missile` command
introduced in API v125 instead of the deprecated probe-level launch route,
while preserving typed confirmation, live inventory/Manny/target validation,
and the existing opt-in emergency escape boundary.

The reviewed contract also recognizes the server-authoritative seven-day Manny
`waiting_for_space` timestamp and API v124 asteroid-impact alert delivery. The
game now sends launcher results only when the launcher remains in the impact
sector and sends a separate critical damage alert to an impacted probe or
Others ship.

## Skunkworks 1.0.6

Skunkworks 1.0.6 reviews and integrates Von Neumann Game API v116–v122. Manual
Control adds a fifth **Combat Control Systems** tab for explicitly confirmed
probe missile launches, moving-projectile telemetry, and a per-probe opt-in
emergency escape to a random eligible nearest sector.
Missiles are also available as ordinary production stockpile targets; crafting
them does not authorize Skunkworks to launch them.

When a missile targets the focused probe, its critical warning replaces Live
Sector with an impact countdown and a button that opens Combat Control
directly. Missile alerts remain in-app in this patch; operating-system desktop
notifications remain planned for 1.1.

Movement is blocked locally below the API's exact 10% integrity threshold.
Expired task timers now say **Awaiting Server Completion**. Planets are
selectable on Live Sector, expose detailed resource information, can be
inspected and mined when the API permits it, and contribute a separate
planetary resource count. Unusual artificial mining targets require explicit
approval under Resources.

The patch also fixes depleted-asteroid grouping when older observations carry
both resource hints and zero authoritative amounts, accepts direct decimal ECE
values for same-sector Deuterium transfers, and rounds recipe raw-resource
totals to two decimals.

## Skunkworks 1.0.5

Skunkworks 1.0.5 keeps the development footer synchronized with the version in
the active source tree, adds Integrated Circuits to automation production
targets alongside SCUT relays and transit beacons, and treats existing safety
history as the startup baseline instead of a new notification after every
restart.

The live sector map now condenses two or more depleted asteroids into one
counted marker while leaving resource-bearing asteroids individually visible.

## Skunkworks 1.0.4

Skunkworks 1.0.4 restores sector-object inspection as an explicit Manny Field
Operations control and recognizes equivalent hyphenated, spaced, camel-case,
and snake-case object types. This also prevents live dormant constructs and
SCUT relays from disappearing from Manual Control because of an API spelling
variant. Empty SCUT steps now explain which visible relay prerequisite is
missing.

Focused secondary probes now receive a lightweight alert and damage-warning
sync independently of the slower default-probe archival import. Newly observed
alerts pulse the Safety tab in red until Safety is viewed.

An Unauthorized/401 response on first launch is now identified as an API-key
problem and offers direct API-key re-entry while preserving all local history
and settings.

## Skunkworks 1.0.3

Skunkworks 1.0.3 restores verified neighbor connection lines at every settled
Galaxy Map zoom distance. The interaction optimization still suspends those
expensive links while the camera is actively moving, then restores them after
the view settles.

A new **Fit Map** control centers and zooms the camera to contain all sectors
currently admitted by the map filters. Automatic camera clipping keeps large
discovered areas visible at the resulting overview distance.

## Skunkworks 1.0.2

Skunkworks 1.0.2 improves galaxy-map responsiveness as explored space grows.
During camera motion and distant overview, the map temporarily suppresses its
large link mesh and uses lower-cost sector markers; full detail returns shortly
after the view settles. Pan buttons now move relative to the camera's current
right and up directions instead of fixed world axes.

Mission Control alert previews are clipped and shortened inside their dashboard
cards. The complete alert text remains available in Safety.

Linux and other source installations now explicitly package the `src` modules,
QML, and assets, so the installed `skunkworks` launcher works outside the source
checkout without setting `PYTHONPATH`.

The installation guide and operator manual now contain a prominent safe-update
procedure. Application packages remain separate from accumulated user data;
operators should back up the database, replace only the application, and retain
the same platform data directory and `SKUNKWORKS_HOME` setting.

## Skunkworks 1.0.1

Skunkworks 1.0.1 fixes first-launch fleet loading in unsigned windowed
packages. PyInstaller GUI applications may not have an attached terminal;
Skunkworks now treats a missing or detached standard-input stream as
non-interactive and opens the remembered or default probe normally instead of
reporting that live fleet data is unavailable.

This patch contains no game-data, planner, automation-policy, or persistence
changes. All 436 automated tests pass across the corrected source tree.

## Skunkworks 1.0.0

Skunkworks 1.0.0 is the first public desktop release of policy-controlled mission
control and fleet automation for the Von Neumann Game. Skunkworks is released
under the GNU General Public License, version 3. Recipients may modify and
redistribute it under GPLv3's corresponding-source, notice, and modified-version
requirements.

Created by Christopher Ziegenhagel, aka Ziegenbagel, for the Von Neumann Game.

Highlights include multi-probe mission control, manual and automatic travel,
galaxy mapping, production and assembly planning, Manny field operations,
container routing, reserve-tanker logistics, communications and logbooks,
per-probe roles, explainable priorities, live preflight checks, execution
allowlists, leases, and emergency stop.

The local data engine keeps durable operational history, deduplicates unchanged
world observations, compacts older telemetry, supports verified online backups,
and exposes database integrity and size reports. Runtime snapshots and diagnostic
logs are bounded.

Begin in Observe Only mode, verify the focused probe and execution policy, and
review proposed commands before enabling automatic live orders. Automatic daily
Logbook reports remain opt-in through the Logbook checkbox.

The first public packages are unsigned portable builds. Verify the published
SHA-256 checksums before opening them. On macOS, move only `Skunkworks.app` to
Applications. A temporary Keychain **Allow** choice is requested again on the
next launch; **Always Allow** persistently authorizes access to the stored game
API key. Installation, upgrade, rollback, and support instructions accompany
the release.
