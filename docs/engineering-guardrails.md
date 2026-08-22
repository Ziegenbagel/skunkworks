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

## Persistence Invariants

### History must not grow once per refresh without a material change

Separate UI and automation workers may observe identical sector/resource state.
Deduplicate material world-history signatures across service instances. The
database previously reached 5.6 GB with about 62,000 sector observations and one
million resource rows for a modest fleet.

### Local reads must stay bounded

- Configure persistent SQLite WAL mode once per DataEngine, not on every short-
  lived connection.
- Live task labels query a bounded recent set of successful actions rather than
  loading the full journal.
- Galaxy reconstruction selects the latest observation per sector and uses its
  cache until a meaningful discovery or arrival invalidates it.

### Compaction preserves operational truth

`DataEngine.compact_history()` retains recent high-resolution telemetry, daily
older probe/resource samples, and the latest observation for every probe-sector
pair. It never removes preferences, operations, roles, visits, archive reports,
event state, execution leases, or action history. Physical `VACUUM` requires an
exclusive maintenance boundary and must not run underneath a live application.

Relevant code/tests:

- `src/data/engine.py`
- `tests/test_data_engine.py`

## API and Safety Invariants

- Explicit probe ID is required at every probe-scoped gateway.
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

