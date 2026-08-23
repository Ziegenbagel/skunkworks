# Skunkworks Privacy

Skunkworks is a local desktop client. It does not operate a Skunkworks telemetry
service or sell user data. It communicates with the Von Neumann Game service
selected by the application to retrieve game state and submit operator-approved
or policy-approved game commands.

The API key is stored in the operating-system credential vault. Developers may
instead provide `VON_NEUMANN_API_KEY` in the process environment. The key is not
written to the SQLite database, settings JSON, snapshots, or diagnostic logs.

Skunkworks stores game observations, operational preferences, action history,
messages, alerts, missions, and generated reports in a local SQLite database.
It also keeps bounded runtime sector snapshots for diagnostics. These records
may contain probe names, player-visible messages, coordinates, inventory, and
other game account data. Diagnostic logs rotate at 1 MiB with five backups and
redact common credential forms, but users should still inspect any support
bundle before sharing it.

Removing the API key from Settings deletes the vault credential. Uninstalling
the application may not remove the local database, snapshots, backups, or logs;
those are retained so an uninstall does not silently destroy operational
history. Exact platform locations are documented in
`docs/installing-and-updating.md`.

Backups are local files chosen by the operator. Skunkworks does not upload them.
The game service's own privacy terms govern data processed by that service.
