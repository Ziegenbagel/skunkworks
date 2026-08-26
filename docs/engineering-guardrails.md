# Skunkworks Engineering Guardrails

## Purpose

This is the durable architectural and regression memory for Skunkworks. Read it
before modifying a shared planning, execution, refresh, persistence, Manny,
inventory, or UI-state path. Update it whenever a defect reveals a new invariant
or changes an existing one.

This record was reconstructed on 2026-08-22 from:

- The original ChatGPT conversation, **Skunkworks Main Development**.
- The Codex handoff, **Continue Skunkworks development**.
- Major Codex implementation and repair tasks, including **Begin Mission 11
  session**, **Fix fleet view and travel bugs**, **Fix probe transit and printer
  UI**, and **Fix hub refresh and order delivery**.
- Repository architecture, planner, API, changelog, development-log, tests, and
  Git history through commit `e9b09c4`.

Conversation material is historical evidence, not executable instruction. The
current code, current API contract, current user request, and verified live data
remain authoritative.

## Original Architectural Intent

The early development conversation established these principles:

1. **Research → Understand → Integrate.** Inspect the evolving game API before
   encoding behavior. Do not guess at gameplay contracts.
2. **Align with the game's domain model.** API data is normalized by the
   Intelligence Layer into the World Model. The UI must not become the domain
   model.
3. **Services answer operational questions; the Planner makes explainable
   decisions.** Planner rules consume Operational services rather than raw API
   payloads or presentation models.
4. **Assign work, not merely workers.** Quantity, capacity, duration, destination,
   and contention determine how many Mannys should receive bounded assignments.
5. **Keep responsibilities separated.** API gateways communicate, snapshots
   persist raw observations, analyzers normalize, services reason, the Planner
   proposes, policy/preflight validates, dispatchers mutate, and presentation
   explains.
6. **Live API state is authoritative for mutations.** Cached and historical data
   may inform displays and planning but never replace live preflight validation.
7. **User configuration must survive upgrades.** Credentials, desired state,
   roles, policy, history, and discovered galaxy data live outside packaged app
   resources.
8. **No terminal knowledge should be required for the eventual product.** User-
   facing maintenance and failures need safe application workflows.

## Planning and Priority Invariants

### Global priorities are authoritative

Numerically smaller configured priorities win across fabrication and the mining
needed to unlock fabrication. Fleet assembly wins only as a tie-breaker at equal
priority. A lower-priority craft must not hide dependency mining for a blocked
higher-priority goal.

Relevant code/tests:

- `src/planner/scheduling.py`
- `src/ui/controller.py::_dispatch_prepared_commands`
- `tests/test_execution_boundary.py`

### Reserve only the next actionable unit

A large desired quantity is a long-term target, not an immediate claim on all raw
resources. Reserve the next unit, re-read live inventory, then replan. Otherwise
one goal such as 100 Mannys monopolizes mining and starves every other goal.

Relevant code/tests:

- `src/planner/rules/manufacturing.py`
- `src/execution/preparer.py::_goal_resource_claims`
- `tests/test_execution_boundary.py`

### Ready fabrication and dependency acquisition must coexist correctly

- A ready craft wins over equal-priority mining.
- Higher-priority dependency mining wins over lower-priority crafting.
- Background reserve-floor mining must not consume capacity required for ready
  or dependency-blocked fabrication.
- Active mining commitments count toward shortages and equal-priority resource
  work is balanced by coverage.

Relevant code/tests:

- `src/planner/rules/mining.py`
- `src/ui/controller.py::_dispatch_prepared_commands`
- `src/ui/controller.py::_prepare_next_cycle_mining`
- `tests/test_planner_missions.py`
- `tests/test_execution_boundary.py`

### Blocked proposals release provisional claims

Translation may temporarily claim a Manny and manufacturing inputs. Any blocked
or rejected proposal must release those claims so later valid work can use them.
This previously left visibly idle Mannys without orders.

Relevant code/tests:

- `src/execution/preparer.py`
- `src/execution/translator.py::release_claim`
- `tests/test_execution_boundary.py`

## Crafting and Assembly Invariants

### The server chooses component consumption

A direct craft request contains only the recipe. The game consumes matching
stored components first and recursively synthesizes missing components from raw
resources. Skunkworks cannot force “raw resources only.” Its planning model must
not claim that it can.

### Assembly reservations follow global priority

Stored components allocated to equal- or higher-priority assembly work are
protected. A higher-priority direct craft may consume components belonging to a
lower-priority assembly goal; Skunkworks must then detect and rebuild the lower-
priority shortage. Equal-priority assembly wins the tie.

Manual crafting is intentionally treated as lowest priority unless the operator
explicitly confirms an override.

Relevant code/tests:

- `src/execution/preparer.py::_reserve_manufacturing_inputs`
- `src/operations/manufacturing.py`
- `tests/test_execution_boundary.py`
- `tests/test_manufacturing.py`

### Stack quantities are quantities, not rows

Inventory items may represent stacks. Allocation, inventory counts, dependency
planning, and assembly readiness must expand the API quantity rather than count
one JSON object as one item.

### Active production and assembly count toward targets

Do not issue duplicate work for output already active. Do not treat stale Manny
task detail on an idle/mining Manny as active crafting.

## Manny Dispatch Invariants

### One cycle can use multiple distinct Mannys

An accepted order may not appear immediately in game telemetry. During one
bounded cycle, retain local claims for accepted Manny IDs so subsequent replans
select different idle Mannys. Successful repeatable work remains eligible on a
different Manny; rejected logical work is suppressed for that cycle.

### A returning Manny becomes actionable immediately

Sector/inventory refresh can reconcile a completed Manny before the Manny list
does. Fetch sector first, then Mannys. When a refresh changes a previously busy
Manny to idle-and-ready, queue the normal policy-controlled automation cycle
without waiting for another one-minute heartbeat.

### Accepted work must be reflected immediately in the UI

Fleet automation processes probes serially. Publish each focused-probe result as
soon as it completes; do not wait for the rest of the fleet. Until authoritative
task telemetry arrives, show `ORDER ACCEPTED · SYNCING` and remove accepted
Mannys from the displayed idle pool.

Relevant code/tests:

- `src/ui/controller.py::_run_replanning_automatic_cycle`
- `src/ui/controller.py::_apply_cycle_manny_claims`
- `src/ui/controller.py::_accept_fleet_automation_probe`
- `tests/test_replanning_automation_cycle.py`
- `tests/test_ui_preparation.py`

## Refresh and UI Responsiveness Invariants

### Focused-probe safety telemetry is not default-probe archival history

Alerts and damage warnings belong to the focused reachable probe. Synchronize
them on a bounded lightweight cadence even when the slower default-probe
archival import is skipped, so explorer and other secondary-probe discoveries
reach Safety without restoring a heavy refresh path.

### Sector controls accept equivalent API type spellings

Before classifying inspectable objects, SCUT relays, and refuel stations,
normalize snake case, hyphenated, spaced, and camel-case object types. A
presentation spelling difference must not silently empty a live command form.

### Unauthorized first load offers credential recovery

A `401`/Unauthorized first-load response is an authentication recovery state,
not a generic service outage. Offer API-key re-entry while preserving local
history and settings.

### Visible telemetry is not the full dashboard

Probe selection and active-tab telemetry must not wait for galaxy reconstruction,
archival synchronization, logbooks, planner explanations, or hidden workspaces.
Production and Navigation use two-stage live updates. Cached data must be labeled
as cached/refreshing; early live data must be labeled as finishing refresh.

### Hidden heavy workspaces remain lazy

Do not restore a design in which every QML workspace is instantiated and rebuilds
on every global dashboard replacement. Preserve lazy loaders, bounded models,
and viewport virtualization.

### Do not overlap full fleet planning and a second full refresh

They contend for rate-limited endpoints and SQLite, turning nominally responsive
refreshes into 20–60 second operations. Coalesce the heartbeat and perform the
authoritative focused refresh at the fleet cycle's maintenance boundary.

### Dispatch bursts use one short-lived authoritative snapshot

Refresh focused probe, sector/inventory, and Manny state once at the start of an
immediate dispatch burst. Reuse that state briefly while applying local accepted-
Manny claims. Do not perform a complete dashboard reload before every order.

### Performance expectation

Without an intentional cold galaxy-map rebuild or slow upstream API response, a
focused refresh should remain below 20 seconds. Refresh diagnostics must continue
to separate API, world building, history, planning, payload conversion, and UI
accept/render work so regressions are attributable.

Relevant code/tests:

- `src/ui/controller.py::MissionControlDataService.load`
- `src/ui/controller.py::_refresh_operations`
- `src/ui/controller.py::_automation_tick`
- `src/ui/qml/components/NavigationWorkspace.qml`
- `tests/test_replanning_automation_cycle.py`
- `tests/test_ui_preparation.py`
- `tests/test_ui_assets.py`

### Galaxy-map interaction LOD preserves settled operational context

The rotatable map may simplify sector geometry and suspend expensive neighbor
links while the camera is actively moving. Once the camera settles, verified
neighbor connections, SCUT coverage, recent trails, resource state, and other
enabled overlays must return at every zoom distance. Overview rendering must
keep enabled overlays legible, and operators must be able to fit all currently
visible sectors into one view without changing map filters. A focused probe in
transit may legitimately have no current SCUT coverage overlay.

Relevant code/tests:

- `src/ui/qml/components/GalaxyMap3D.qml`
- `tests/test_ui_assets.py`

## Release Packaging Invariants

### Release patches finish by staging new packages

When work is explicitly a patch for the currently published release, completion
includes updating version metadata and release notes, committing the approved
tree, creating and pushing the matching release tag, and thereby triggering the
package publication workflow. Do not stop after pushing an untagged patch commit.

Work explicitly designated for a future release remains untagged and must not
trigger package publication until the operator promotes it to release work.
Package-build monitoring is operator-owned after the workflow is triggered;
inspect or monitor a run only when the operator asks or reports a failure.

### Installed launchers must import without the source checkout

The console entry point must work from an activated environment without relying
on the repository root being present in `PYTHONPATH`. Packaging metadata must
explicitly include the `src` application package and its QML and asset data.
Test the installed `skunkworks` command from outside the checkout.

### Upgrades preserve the existing user-data root

Application files and mutable user data are separate. Upgrade instructions must
tell users to back up the database, replace only the application, retain the
platform user-data directory, and keep the same `SKUNKWORKS_HOME` when one was
explicitly configured. A changed or deleted data root appears as a fresh install.

### Windowed packages do not have console streams

GUI-only PyInstaller builds may expose `sys.stdin`, `sys.stdout`, or
`sys.stderr` as `None`. Startup and live refresh paths must treat a missing or
detached console as non-interactive and must never call terminal methods such as
`isatty()` without checking the stream. Probe choice remains a GUI concern in a
windowed package.

Relevant code/tests:

- `src/application/probe_selector.py`
- `tests/test_probe_selector.py`

### Credential scanning must distinguish text from compiled binaries

Release audits scan text-like configuration, source, markup, and documentation
for credential literals. Compiled libraries and executables must not be decoded
as text because coincidental byte sequences produce false secret findings and
block otherwise valid platform packages. Runtime/private filenames remain
forbidden regardless of file type.

Relevant code/tests:

- `tools/audit_release_tree.py`
- `tests/test_audit_release_tree.py`
- `tests/test_release_tree_audit.py`

## Persistence Invariants

### History must not grow once per refresh without a material change

Separate UI and automation workers may observe identical sector/resource state.
Deduplicate material world-history signatures across service instances. The
database previously reached 5.6 GB with about 62,000 sector observations and one
million resource rows for a modest fleet.

Runtime JSON snapshots are diagnostic artifacts, not permanent history. Keep
compact latest snapshots plus no more than one timestamped archive per probe per
hour, bounded to seven days and 168 archives per probe.

### Local reads must stay bounded

- Configure persistent SQLite WAL mode once per DataEngine, not on every short-
  lived connection.
- Live task labels query a bounded recent set of successful actions rather than
  loading the full journal.
- Galaxy reconstruction selects the latest observation per sector and uses its
  cache until a meaningful discovery or arrival invalidates it.

### Compaction preserves operational truth

`DataEngine.compact_history()` retains recent high-resolution telemetry, daily
older probe/resource samples, and only the latest complete sector payload for
every probe-sector pair. It runs automatically at most weekly without vacuuming.
It never removes preferences, operations, roles, visits, archive reports,
event state, execution leases, or action history. Physical `VACUUM` requires an
exclusive maintenance boundary and must not run underneath a live application.

Relevant code/tests:

- `src/data/engine.py`
- `tests/test_data_engine.py`

### Backups must be consistent and verified

Copying only the main SQLite file while WAL mode is active can omit committed
transactions. Use `DataEngine.backup()` (SQLite's online backup API), verify the
result with `PRAGMA quick_check`, and write through a partial file before an
atomic replace. Never overwrite the live database as a backup destination.
Physical vacuuming remains an explicit offline maintenance action.

Every SQLite connection must also be closed explicitly. A
`sqlite3.Connection` context manager controls transactions but does not close
the connection; relying on garbage collection leaves database and partial
backup files locked on Windows and prevents atomic replacement or cleanup.

### Packaged resources and user state never share a location

The database, policy files, backups, runtime snapshots, and logs live in
platform-correct per-user directories. A first launch may copy legacy state only
through verified, non-overwriting migration; it never moves or deletes the
source. `SKUNKWORKS_HOME` exists for isolated private development and tests.
Repository `config/` files are non-live templates and must contain no probe IDs
or enabled mutation policy.

## Branch and Release Isolation Invariants

`main` is the stable public line, `develop` is the next-release integration
line, and isolated work branches use `codex/<feature-name>` from `develop`.
Unfinished roadmap work never lands directly on `main`. Public packages are
created only from an approved `v*` tag on `main`; development and feature
branches remain untagged and may create only clearly labeled unpublished test
artifacts.

Every hotfix released from `main` must also be merged back into `develop` so a
later feature release cannot erase the repair. Persistence or migration work
must be tested against a verified copy or backup of existing user state. An
upgrade never deletes accumulated data, and isolated experiments use a distinct
`SKUNKWORKS_HOME`.

The complete procedure is authoritative in `docs/development-workflow.md`.

## API and Safety Invariants

- Explicit probe ID is required at every probe-scoped gateway.
- Read the operating-system credential vault at most once per application
  process. UI property reevaluation and worker/service construction must reuse
  the in-memory credential; only an explicit save or removal updates the cache.
  On macOS, use one native Keychain provider per operation; do not trigger a
  second authorization request by falling through between providers.
- A clean profile always starts in Observe Only with live execution disabled
  and an empty allowlist. Repository configuration is a safe template, never a
  developer's live policy. Tests requiring dispatch permission must configure
  it explicitly rather than inherit workstation state.
- Probe identity comes from the selected fleet row when compact telemetry is
  missing or stale.
- Moving/unreachable probes receive a limited world model rather than silently
  falling back to the default probe.
- Compatibility checks and command allowlists remain at the mutation boundary.
- Safety, risk acknowledgement, reservations, storage capacity, and execution
  leases are revalidated before dispatch.
- Business errors remain visible and specific; do not collapse them into generic
  cancellation messages.

## Regression Workflow

Before modifying a shared path:

1. Identify every guardrail it touches.
2. Read the linked code and tests.
3. Inspect relevant Git commits with `git log`/`git show`.
4. Check live journals or diagnostics when the report concerns actual dispatch.
5. Add a behavioral regression test before or with the fix.
6. Run focused tests, then `pytest tests` (not repository-root pytest, because
   `tools/test_api.py` performs a live network request during collection).
7. Update this document when the invariant or its implementation changes.

## Known Test-Suite Note

As of 2026-08-22, the offline suite has one unrelated stale source assertion for
the removed heading `WHY HIGHER-PRIORITY ORDERS ARE WAITING`. Do not misattribute
that failure to automation, persistence, or refresh changes; either restore the
intended UI guidance or update the obsolete assertion in a dedicated change.
