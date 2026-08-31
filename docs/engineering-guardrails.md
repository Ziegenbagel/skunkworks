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

### A deuterium reserve tanker replenishes its transferable surplus

Assigning `deuterium_reserve` is an operational commitment, not only a transfer
label. While that role is assigned to a deuterium tanker, planning adds an
effective refill-to-100% fuel goal at high priority so the tanker mines back to
full after preserving its protected reserve and supplying the next probe in its
configured chain. The operator's ordinary saved fuel target remains unchanged
and becomes effective again if the role is removed.

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
Planner reconciliation is an equivalent readiness boundary: when a durable
move fingerprint changes from blocked to ready after Manny work completes,
queue one immediate policy-controlled cycle even if the Manny was already in
the prior visible idle pool. An unchanged ready fingerprint must not create a
post-refresh dispatch loop.

### Accepted work must be reflected immediately in the UI

Fleet automation processes probes serially. Publish each focused-probe result as
soon as it completes; do not wait for the rest of the fleet. Until authoritative
task telemetry arrives, show `ORDER ACCEPTED · SYNCING` and remove accepted
Mannys from the displayed idle pool.

Manual mining bursts follow the same local-claim rule. Immediately append each
reviewed order to a controller-owned FIFO, mark its Manny as `MINING ORDER
QUEUED`, and remove that Manny from the visible idle pool before the preceding
network request finishes. One background worker drains the FIFO serially, so a
slow API response never disables selection of another idle Manny and concurrent
orders cannot race the same live state. Accepted orders remain locally claimed;
rejected orders restore their Manny. Do not start a full dashboard refresh after
every order—the next scheduler-owned authoritative refresh reconciles the batch.
The pending total includes the order currently being sent as well as the waiting
tail; popping or dispatching the FIFO head must never make the UI report zero
while work is in flight. Removing one claimed Manny must preserve a valid
selection whenever another idle Manny remains.
Accepted manual mining orders remain in the visible pending-sync total until an
authoritative refresh for their probe arrives. Network acceptance must not emit
a second full dashboard replacement: the enqueue mutation already claimed and
marked that Manny, so only the lightweight queue notice changes on completion.
Manual crafting uses the same optimistic-claim and serial-FIFO boundary. Each
selected Manny disappears from both crafting and inventory idle models before
the preceding request completes; accepted builds remain pending-sync until the
scheduled authoritative refresh, and a reservation conflict restores that Manny
before presenting the one-order override. Never refresh between accepted builds
in a user-entered batch.

Deuterium mining refills the probe tank and must not include a detached storage
`targetContainerId`. Resource-routing rules may select detached destinations for
ordinary cargo, but applying them to deuterium produces an API rejection and
leaves an otherwise valid reserve tanker visibly idle.

Automatic travel requires every owned Manny to be aboard and available at both
planning and last-mile preflight, except for an explicit recovery hop whose
target is the exact reported sector of an already off-probe Manny. A Manny command accepted earlier in the same
dispatch burst immediately invalidates a previously prepared movement command;
the probe must wait for authoritative task completion and return telemetry
before continuing its durable route.

During the API movement-preparation grace period, automatic planning checks the
same invariant again. If any owned Manny is still working, unavailable, or off
probe, dispatch the canonical movement cancellation after live preflight and
retain the durable destination; cancellation must not erase the route that will
resume after every Manny is aboard. Never cancel a preparing recovery hop whose
live target is the reported sector of the missing Manny.

Movement idempotency is authoritative-state based. The action journal records a
move as succeeded when preparation is accepted, but that does not prove the hop
completed: a subsequent safety cancellation may leave the probe at its origin.
A ready move with the same fingerprint must therefore pass through fresh live
preflight and dispatch again. Historical fingerprints remain hard idempotency
guards for genuinely one-time mutations such as probe assembly.

A secondary travel-risk acknowledgement is never generic. The queued command
must display every live warning code and its human-readable reason—including
the concrete expected and worst-case values supplied by the safety assessment—
beside the acknowledgement control before the operator can accept it.

Relevant code/tests:

- `src/ui/controller.py::_run_replanning_automatic_cycle`
- `src/ui/controller.py::_apply_cycle_manny_claims`
- `src/ui/controller.py::_accept_fleet_automation_probe`
- `tests/test_replanning_automation_cycle.py`
- `tests/test_ui_preparation.py`

## Refresh and UI Responsiveness Invariants

### Operator actions never occupy the Qt UI thread

API requests, live preflight, credential-vault access, SQLite writes, route
calculation, and post-command synchronization triggered by buttons or settings
must execute through a background worker. The initiating slot returns
immediately, exposes a visible sending/saving state, and applies results on the
Qt thread. Accepted commands use a focused lightweight sync; they do not force
unrelated archival work before the interface becomes usable again.

This boundary applies to every feature added for 1.1 and later, including small
preference toggles and apparently local safety bookkeeping. Qt properties and
dashboard-acceptance callbacks must consume in-memory or worker-prepared values;
they must not open SQLite or policy files during QML reevaluation or refresh
application. Fleet eligibility scans, travel-consent persistence, onboarding,
combat-safety settings, unusual mining approvals, and handled-missile history
all belong off-thread. A completion callback may update in-memory presentation
state, emit signals, and schedule the next worker, but must not perform the
durable read or write itself.

Notification candidate extraction may use the accepted in-memory dashboard,
but restart-safe `seen` persistence is also background work. Coalesce a newer
dashboard while that worker is active rather than writing from the dashboard
acceptance callback or starting overlapping SQLite writers.

Production scrolling and Galaxy Map camera interaction are interaction
boundaries. Dashboard updates may be coalesced until a production flick settles,
and camera LOD may hide expensive geometry, but neither path may destroy and
recreate its full delegate/model population for every wheel or drag event.
Galaxy payloads carry a worker-computed content revision. Equivalent global
refreshes retain the existing 3D model, updates arriving during camera movement
are applied only after settling, and expensive overlays are hidden through one
parent scene node rather than toggling every delegate binding individually.
The same revision boundary applies to high-churn workspaces. Full refresh
payloads compute section revisions in the worker. Production and Manual Control
retain their accepted models when only an unrelated section changes, while
controller-side optimistic mutations explicitly invalidate only the sections
they changed. Heavy workspace construction is asynchronous so switching tabs
cannot monopolize the event loop. Galaxy and Manual Control may remain retained
after their first construction because their large inputs are revision-gated;
do not retain an expensive workspace whose hidden bindings still consume every
global dashboard replacement. The Qt/QML boundary receives a projection of the
accepted dashboard sized for the visible workspace; hidden galaxy, history,
communications, production, and manual-control graphs remain in the controller
and must not cross that boundary during an unrelated workspace refresh. A
revision-gated cache may accept a revision only when that section's projected
payload is present; an unrelated projection carrying the same global revision
must never replace a retained workspace with empty fallback models. A
lightweight GUI timer records interactive
event-loop stalls separately from API and worker timing; recording a stall must
not itself emit a dashboard replacement.
Stall diagnostics must retain enough bounded, privacy-safe attribution to be
actionable: active section, latest UI activity, activity/dashboard age, refresh
state, and dashboard generation. Dashboard notification-to-next-event-loop
settle time is distinct from worker refresh time. Heavy workspace loaders report
loading and ready boundaries, and stalls of at least 500 ms enter the rotating
diagnostic log. Attribution history remains bounded and contains no API payload,
credentials, messages, coordinates, or resource inventory.
Navigation audio is part of the interaction boundary. Keep its common effect
preloaded and replay the existing source; repeatedly assigning the same media
URL can synchronously rebuild the macOS AVFoundation player and make every tab
change appear to be a rendering stall.
Recurring presentation bindings must be self-contained and exception-free:
countdown ticks may not call functions absent from their component, and controls
must not assign negative model indices while asynchronously loaded models are
temporarily empty. Repeated QML warnings are a responsiveness regression even
when the interface remains visually usable.
The background refresh converts Python containers to QML-safe lists and maps;
every controller-side incremental dashboard mutation must preserve those same
shapes. Reintroducing tuples after conversion makes JavaScript array methods
fail and causes Qt controls to report invalid model sizes on every refresh.
Dialogs must have a non-circular width owner rather than deriving implicit width
from content whose width depends on the dialog's available width.

Relevant code/tests:

- `src/ui/controller.py::_run_background_call`
- `src/ui/qml/components/NavigationWorkspace.qml`
- `src/ui/qml/components/GalaxyMap3D.qml`
- `tests/test_ui_preparation.py`
- `tests/test_ui_assets.py`
- `tests/test_credentials.py`
- `tests/test_fleet_naming.py`

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
The focused-probe selector remains interactive during refresh because the
controller already coalesces a requested probe change and runs it after the
active worker. A background refresh may mark data as syncing, but must not make
unrelated navigation controls appear globally disabled.

### Existing safety history is not a new-session notification

Alerts present in the first live dashboard payload establish the session
baseline. Only alerts first observed after that baseline may pulse the Safety
navigation item; reopening Skunkworks must not relabel unchanged history as new.
That baseline is probe-scoped. Switching probes or returning to one must not
compare its cached alert history against another probe's viewed keys and flash
the Safety tab; only alerts arriving after that probe's baseline may pulse it.

### Hidden heavy workspaces remain lazy

Do not restore a design in which every QML workspace is instantiated and rebuilds
on every global dashboard replacement. Preserve lazy loaders, bounded models,
and viewport virtualization.

### Completed arrival is stationary in operator-facing fleet status

The game fleet API may retain `arrived` as a probe's movement phase long after
travel completed. Fleet selectors and cards present that terminal phase as
`idle`; active phases such as preparing, accelerating, cruising, traveling, and
decelerating remain visible. This is presentation normalization only and must
not rewrite the authoritative movement telemetry used by planning or safety.

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

### Low Power mode never delays operational safety or dispatch

The Low Power profile may reduce stale-tolerant archival imports, background
probe breadth, and distant map detail. It must not lengthen the one-minute
automation heartbeat or defer Stop, focused safety telemetry, active-operation
reconciliation, or an explicitly focused probe refresh. Enabled map overlays
must still return when camera interaction settles.

Relevant code/tests:

- `src/application/operating_profile.py`
- `tests/test_operating_profile.py`

### Auto operating profile is idle-driven and wakes immediately

Auto is a persisted operator choice, while Normal or Low Power is the visible
effective profile. Auto may enter Low Power only after the configured interval
without keyboard, mouse, click, touch, or wheel input. The first such operator input
must restore Normal behavior immediately. Changing the effective profile must
not restart or lengthen the one-minute automation heartbeat, trigger a second
full refresh, or alter Stop, focused safety, and active-operation semantics.
The configured and effective profile names must both be exposed to the UI so
the operator can distinguish `AUTO → NORMAL` from `AUTO → LOW POWER`.

Scheduled operating profiles use local wall-clock `HH:MM` boundaries. Daily
windows repeat and must support crossing midnight. A once-only window resolves
to the next selected start, returns to Normal after its end, and remains visibly
completed rather than silently scheduling itself again. Scheduling changes only
stale-tolerant Low Power behavior; operational safety and dispatch invariants
remain immediate.

Relevant code/tests:

- `src/application/operating_profile.py`
- `src/ui/controller.py`
- `src/ui/qml/components/AutomationSettings.qml`
- `tests/test_operating_profile.py`
- `tests/test_ui_assets.py`

### Desktop notifications are advisory and restart-safe

Desktop notifications are opt-in. Refreshes and restarts must not replay the
same alert or operation result, and delivery must never mark a game alert
viewed or prove that a command succeeded. Notifications are available only
while Skunkworks is running; background continuation is outside 1.1 scope.
Candidate extraction may run in a worker, but its completion returns through a
declared controller slot and desktop delivery uses a GUI-thread-owned QObject;
an unscoped callback must not invoke the tray icon from a worker thread. A new
authoritative operation result must not be overwritten by the previous
dashboard result before notification extraction.
Settings must expose the platform capability and a test action. A successful
test request must be labeled as requested, never as confirmed OS delivery,
because desktop policy can suppress a banner after Qt accepts it.

Relevant code/tests:

- `src/application/notifications.py`
- `tests/test_notifications.py`

## Release Packaging Invariants

### Published release notes are operator-facing bullet lists

Every tagged and publicly packaged Skunkworks version has its own heading in
`RELEASE_NOTES.md`, followed only by concise bullet points describing changes
and fixes an operator can see, use, or reasonably care about. Do not publish
development chronology, branch or merge details, API-analysis activity, test
counts, implementation-layer terminology, or statements about work that did
not change the released application. When numerous small internal corrections
are not individually useful to operators, summarize them with a final
`Other various fixes.` bullet.

Development release drafts stay outside `RELEASE_NOTES.md`. Before tagging, add
the final version section, confirm it includes every user-visible change since
the previous public version, and audit every bullet for accidental future or
development-only content. Historical release sections retain bullet formatting
so the packaged file remains easy to scan.

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
Test the installed application import from outside the checkout. Python 3.14
skips hidden `.pth` files, so setuptools' current `__editable__...pth` output is
not a valid basis for the launcher. Source and `uv` instructions use a regular
non-editable install until the editable mechanism is verified independently on
every supported Python version.

Relevant files/tests:

- `pyproject.toml`
- `.github/workflows/ci.yml`
- `docs/installing-and-updating.md`
- `tests/test_release_readiness.py`

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

A write-deduplication repair must also include a bounded migration for telemetry
accumulated by older releases. Stopping new duplicate rows while leaving a
recent legacy backlog at full resolution is not a complete growth fix.

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

Only one Skunkworks process may write a given application data root at a time.
Separate test and release instances require separate `SKUNKWORKS_HOME` roots.

Low Power may reduce cosmetic countdown cadence and reuse shared immutable
cartography, but it must not lengthen the one-minute automation heartbeat or
delay safety, active-task reconciliation, Stop, or explicit operator refreshes.

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

Development launch instructions must name the intended writable profile
explicitly. When a checkout has a preserved private test profile, every launch
command includes the same `SKUNKWORKS_HOME`; omitting it would select a clean
platform profile whose safe Observe Only defaults can be mistaken for erased
operator settings.

The complete procedure is authoritative in `docs/development-workflow.md`.

## API and Safety Invariants

### Missile response remains explicit, probe-scoped, and restart-safe

`weapon_targeted` and sector missiles with `targetsCurrentProbe=true` are live
critical safety state for the focused probe. They replace the Live Sector view
with an impact countdown and a direct route to Combat Control, but do not emit
an operating-system desktop notification in 1.0.6. Missile launches remain
manual, require the operator to type `Confirm`, and revalidate the selected
Manny, inventory missile, and public target identifier at dispatch.

Missile dispatch uses the canonical API v125 Manny-scoped
`/mannies/{mannyId}/ignite_missile` route. Do not restore the deprecated
probe-level `/missiles` mutator: actor identity belongs in the route, while the
payload contains only the selected missile and opaque target identifiers.

Emergency missile escape is a separate per-probe opt-in. It may issue at most
one random nearest-sector jump for a newly observed missile identifier, only
after fresh live revalidation confirms the probe is idle, sufficiently fueled,
and at least 10% intact. The ordinary emergency stop disables it.

Remote Manny laser response is also a separate per-probe opt-in. A persistent
historical alert is not authority to recall: the background worker must reload
the live alert and owned Manny list, require one unambiguous Manny identity,
and issue only that Manny's canonical recall command. Successful alert IDs are
remembered across restarts, and the ordinary emergency stop disables the
response. It never moves the carrier probe or selects a combat target.

The API v128 autonomous-unit observation is local sector telemetry. It may
identify a deployed unit and carrier but exposes no absolute coordinates;
Skunkworks must not infer coordinates from opaque IDs.
Do not request that local-sector observation while the focused probe is in an
active travel phase. A 404 absence or documented transient 503 from this
optional route must not reject otherwise valid focused-probe telemetry or leave
the selector on the previous probe.

Autonomous-unit telemetry must not be rendered as a floating overlay over Live
Sector. Operational map space remains unobstructed unless the operator opens a
dedicated detail surface or a critical safety takeover is required.

### API impossibility is not an overridable safety preference

API v121 requires at least 10% probe integrity to prepare movement. Skunkworks
locally blocks values strictly below 10%; exactly 10% remains eligible. Safety
profiles cannot override an authoritative game rejection.

### Unusual mineable structures require automation approval

Planets and asteroids exposed as Manny-mineable are ordinary mining sources.
Automatic mining ignores abandoned or unusual artificial structures until the
operator explicitly approves the opaque object ID in Resources.

Relevant code/tests:

- `src/api/gateways/probes.py`
- `src/operations/travel.py`
- `src/operations/mining.py`
- `src/ui/controller.py`
- `tests/test_api_gateways.py`
- `tests/test_planner_missions.py`
- `tests/test_ui_preparation.py`

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
