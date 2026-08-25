# Skunkworks 1.0.4

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
