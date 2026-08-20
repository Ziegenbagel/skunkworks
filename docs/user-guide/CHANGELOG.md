# Operator Manual Revision History

## API v114–v115 — 2026-08-20

- Reviewed and enabled API v114 alert illustrations and API v115 Anatiform
  Asteroid Sculpting under Manual Control → Asteroid Control.
- Future backward-compatible API versions now produce a visible review warning
  without disabling live commands or automation. Servers older than the minimum
  required contract remain blocked.
- Fixed same-sector transfer target IDs so QML integer values are preserved and
  validated before reaching the game API.
- Evaluate / Run Cycle requests made during a refresh are now queued instead of
  silently discarded.

## API v113 — 2026-08-19

- Reviewed and enabled API v113. Added Manual Control → SCUT Blueprint Sharing
  for sending a known improvement blueprint to another player's probe on the
  same active SCUT network, with recipient filtering and confirmation before
  the live command is sent.

## API v112 — 2026-08-19

- Reviewed and enabled API v112. Added probe-scoped alert and damage-warning
  deletion, motorized-asteroid Manny tasks, asteroid trajectory launch and
  local telemetry routes, and support for the additive motorization and
  improvement-capability fields introduced in API v108–v111.
- Added Manual Control / Asteroid Control for propulsion installation,
  refueling, neighboring-sector transfer, explicitly confirmed local impacts,
  and active trajectory telemetry from detailed sector scans.

## API v107 — 2026-08-13

- Reviewed and enabled API v107. Container controls can atomically reassign
  active crafting-output reservations before detachment or jettison. Moving-
  probe transfer refusals now explain that both probes must arrive before the
  operator retries, without additional polling.

## 0.1 — 2026-08-01

- Added compatibility with the game’s 2026-08-02 crafting-reservation update:
  Production displays Manny task start times, while reserved-container and
  invalid-reservation failures now retain clear business explanations.
- Added a per-probe Maximum per Manny Mining Order setting from 0.05–0.55 ECE
  in 0.05 increments. The planner retains the full uncovered requirement while
  each live order is capped, allowing operators to trade fewer long campaigns
  for faster Manny availability and more frequent replanning.
- Made Settings quantity, priority, reserve, safety-floor, and cycle-limit
  selectors directly editable from the keyboard while retaining their bounds.
- Enlarged Fleet Status counts for double/triple-digit fleets, doubled Resource
  Summary bar thickness, and added bounded sector-map placement: outward orbital
  labels, reserved perimeter slots, and overflow grouping for dense sectors.
- Tightened Resource Summary row spacing so all four thick bars remain inside
  the panel, moved sector perimeter objects to fixed edge buffers, and stacked
  their Manny activity badges away from lateral object labels.
- Reserved the sector map's lower-right zone for SCUT relay/transit-beacon
  infrastructure, moved asteroid Manny activity into staggered inner lanes,
  and changed planet placement to a stable irregular orbital distribution.
- Fixed Save Automation Targets replacing the live fleet-wide probe-role view
  with a role-less desired-state payload and making assigned roles appear as
  Unassigned until the next refresh.
- Added automatic rotating diagnostic error logs for handled UI/API failures
  and uncaught Python exceptions. Settings can open the support-log folder for
  bug reports, and credential-like values are redacted before writing.
- Corrected Settings scope: execution policy and desired-state automation
  values are now stored per probe, while fleet-wide role assignments are
  locked unless the main/default probe is focused. Reordered API credentials
  above Audio and moved planner guidance into Automation Execution.
- Corrected mining production details to prefer the API's current public
  asteroid or planet name instead of exposing its legacy command object ID.
- Reformatted production completion estimates in the user's local timezone
  with a separated date, standard 24-hour clock, timezone abbreviation and UTC
  offset, plus a live hours/minutes/seconds countdown.
- Corrected operational-health classification so notice-only findings, such as
  every Manny currently being occupied, remain visible without incorrectly
  marking the entire system Degraded.
- Consolidated the project documentation into seven maintained references plus
  the Operator Manual and changelog; moved superseded component notes and the
  development diary into a clearly labeled archive.
- Added an automatic compatibility monitor: startup validation plus an
  unmetered `/api/version` check every six hours. A newly unreviewed version
  pauses live API commands and automation, retains the last valid snapshot,
  and displays the detected and supported version ranges.
- Reviewed and enabled Von Neumann Game API v105–v106 compatibility. Added
  preparation-phase movement cancellation with deuterium refund, unread
  message/alert filters at the API boundary, and terminal/atomic Manny-mining
  status language for v106.
- Replaced live-load concept-data fallbacks with explicit service/API error
  screens. Failed later refreshes now retain the last successful snapshot,
  mark it stale, show the underlying error, and provide a retry control.
- Added complete manual inventory controls: stock moves, resource/item jettison,
  asteroid and planet container deployment, detached-object recovery,
  same-sector deuterium transfer, Manny reassignment, and documented two-step
  cross-probe item/container handoffs.
- Added recovery of drifting and detected asteroid-hidden containers, direct
  same-sector whole-container transfers, selectable mining destinations, and
  resource-rule-aware automatic mining-container selection.
- Added Check for Updates beside the Operator Manual and Change Log; it opens
  the official latest-release channel so the operating system can install the
  correct signed package.
- Created the first illustrated operator-manual edition.
- Documented first launch, dashboard controls, probe selection, sector and galaxy maps, navigation, resources, automation priorities, safety controls, audio, and troubleshooting.
- Added the numbered Mission Control dashboard diagram and maintenance contract.
- Added a numbered Settings workspace diagram and fast-access documentation links.
- Scoped execution mode, command permission, allowlist, cycle limit, and dispatch validation to the focused probe.
- Centered the galaxy map on the focused probe's sector by default and added documented drag and button panning controls.
- Added active-production accounting so in-progress components are not crafted twice.
- Added priority-ordered resource and component claims so lower-priority commands cannot spend inputs allocated to planned higher-priority work.
