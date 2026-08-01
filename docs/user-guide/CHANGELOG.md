# Operator Manual Revision History

## 0.1 — 2026-08-01

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
