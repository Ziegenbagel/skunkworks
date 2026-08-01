# Data Engine

## Purpose

The Data Engine gives Skunkworks durable operational memory. Live API state
remains authoritative; SQLite stores observations, history, preferences, and
event records for analysis and mapping.

Default database:

`data/skunkworks.sqlite3`

The database is local and excluded from Git.

## Schema

The versioned schema currently stores:

- Application preferences
- Probe state history
- Sector observations
- Resource history by object and material
- Fleet-wide visited sectors
- Per-probe visited sectors
- Messages
- Alerts
- Damage warnings
- Missions
- Future event domains through a generic event-record table
- Command lifecycle history and per-probe execution leases
- Durable Operations and their resumable current step
- Exclusive fleet-role assignments for probes and Mannys
- Local acknowledgement, priority, and Operation links for synchronized events
- A Skunkworks report archive kept separate from the player-authored game logbook

Schema changes are recorded in `schema_migrations`.

## Startup Synchronization

Every successful application session:

1. Restores the remembered probe when it still exists.
2. Records the selected probe's current normalized state.
3. Records its current sector observation and resources when sensors expose
   them.
4. Synchronizes fleet and selected-probe visit history.
5. Synchronizes messages, alerts, warnings, and missions.

History synchronization is best effort. A temporary failure does not prevent
the live dashboard from operating.

## Map Reconstruction

`DataEngine.galaxy_map()` reconstructs `GalaxyMap` from durable visit history
and the newest observation for each sector. This is the source for future:

- Galaxy and sector map views
- Resource depletion trends
- Exploration coverage
- SCUT network planning
- Mining target selection
- Travel and logistics planning

The Data Engine contains persistence logic only. It does not make planning or
automation decisions.
