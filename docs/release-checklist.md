# Version 1.0 Release Checklist

This checklist separates work that can be verified in the repository from work
that requires signed platform packages or the live game service.

## Automated repository gate

- [x] Unit and integration suite passes (410 tests before this release pass).
- [x] QML lint passes for the application root.
- [x] SQLite history is deduplicated, bounded, and compactable.
- [x] Database integrity, allocation reporting, and verified online backup exist.
- [x] Runtime snapshots and diagnostic logs have retention limits.
- [x] Product metadata has a real description and one synchronized version.
- [x] Privacy, security, support, third-party notice, capability, and draft release
  documents exist.
- [x] End-user package download, source installation, and manual update guidance exists.
- [x] Raw databases and sector snapshots are excluded from the current release tree.
- [ ] Distribution license selected by the owner and added at repository root.
- [ ] Dependency and asset notices regenerated from the exact packaged artifacts.
- [ ] No local `.env`, database, snapshot, log, backup, or developer cache is in
  the staged release payload.

Run:

```bash
python -m pytest -q tests
pyside6-qmllint -I src/ui/qml src/ui/qml/App.qml
python -m tools.release_readiness
git diff --check
```

## Data and upgrade gate

- [ ] Back up a representative existing database and verify integrity.
- [ ] Start the release candidate against a copy of existing 0.7 data.
- [ ] Confirm settings, roles, operations, galaxy history, and action journal remain.
- [ ] Exercise interrupted startup and a full restore from backup.
- [ ] Record database size and focused-refresh timings before and after upgrade.

Useful commands while Skunkworks is stopped:

```bash
python -m tools.database_maintenance
python -m tools.database_maintenance --backup /safe/path/skunkworks.sqlite3
python -m tools.database_maintenance --compact --retain-days 30
python -m tools.database_maintenance --vacuum --retain-days 30
```

`--vacuum` requires an exclusive maintenance window and enough temporary disk
space for SQLite to rebuild the file.

## Live-service acceptance gate

- [ ] Confirm reviewed API v115 behavior for every capability in the matrix.
- [ ] Run observe-only, approval, and automatic modes with each allowlist group.
- [ ] Confirm returning Mannys dispatch, priority inversions, assembly component
  reservations, background mining, and accepted-order syncing.
- [ ] Confirm ordinary focused refreshes stay below 20 seconds unless upstream
  latency or an intentional galaxy rebuild is identified in diagnostics.
- [ ] Complete a multi-hour automation soak with restart and rate-limit recovery.

## Platform packaging gate

- [ ] Build macOS, Windows, and Linux packages from a clean tagged checkout.
- [ ] Store mutable data in platform user-data locations, never package resources.
- [ ] Bundle exact runtime licenses and notices.
- [ ] Sign/notarize where supported, publish checksums, and verify signatures.
- [ ] Install, upgrade, launch, stop, uninstall, and reinstall on clean machines.
- [ ] Verify credential vault, display scaling, audio, manual links, backup, and
  diagnostics on every supported platform.
- [ ] Tag the approved commit and attach final release notes and artifacts.
