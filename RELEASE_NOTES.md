# Skunkworks 1.0.0

Skunkworks 1.0 is the first public desktop release of policy-controlled mission
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
