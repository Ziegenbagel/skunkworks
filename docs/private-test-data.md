# Private Test Data Workflow

Live game observations are valuable regression evidence but are not release
assets. Skunkworks keeps these concerns separate.

## Local private data

The ignored `data/` runtime database, database sidecars, backups, runtime
snapshots, and raw sector snapshots may remain on the developer machine. They
can be used for performance measurements, migration rehearsals, planner
reproduction, and future release work. Removing a file from Git tracking does
not require deleting the private working copy.

For this development checkout, the preserved private runtime is rooted at the
ignored `private/test-data/` directory. It retains the original execution policy
and points to the existing live database without copying it. Launch explicitly
against that private runtime with:

```bash
SKUNKWORKS_HOME="$PWD/private/test-data" python -m src.ui.app
```

On Windows PowerShell:

```powershell
$env:SKUNKWORKS_HOME = "$PWD\private\test-data"
python -m src.ui.app
```

Before high-risk migration or compaction work, make a verified backup outside
the repository:

```bash
python -m tools.database_maintenance \
  --backup /private/backup/location/skunkworks-before-change.sqlite3
```

Never run tests that mutate the only copy of live data. Copy the database into a
temporary directory and point the test or maintenance command at that copy.

## Public regression fixtures

Tests committed to Git must use synthetic identities, reduced coordinates and
inventories, and only the fields needed to reproduce the invariant. A useful
private snapshot should be converted into the smallest sanitized fixture rather
than copied wholesale. Remove player/probe names, messages, object identifiers,
coordinates not required by the test, and unrelated inventory or history.

Screenshots are data too. Public manual screenshots must use a synthetic demo
profile or be visibly anonymized before publication. Keep original screenshots
outside the repository when they are needed as layout references.

## Release enforcement

`python -m tools.release_readiness` fails if Git tracks `.env`, raw snapshot
directories, databases, SQLite sidecars, backups, or logs. Packaging should use
an explicit allowlist and a clean checkout so ignored local files can never be
included accidentally.
