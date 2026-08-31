# Development Release Log

This is the private-to-development candidate ledger for the next Skunkworks
release. It is not a public release note and must never be passed directly to a
GitHub Release or packaged as `RELEASE_NOTES.md`.

Record a concise operator-visible candidate whenever behavior changes on
`develop`. At promotion time, verify each candidate against the final product,
rewrite the approved entries as bullets under the new version in
`RELEASE_NOTES.md`, then clear the promoted candidate section. Commit history
remains the record for internal implementation work.

## 1.1.0 candidates

### User-visible changes and fixes

- Added Normal, Low Power, and scheduled operating profiles, including daily or
  one-time start and end times.
- Added opt-in desktop notifications with platform availability and test status
  shown in Settings.
- Fixed live desktop alerts, approvals, failures, and operation notifications
  so they use the same reliable macOS delivery path as the test notification.
- Made manual orders, scans, communications, logbook actions, credential
  operations, and settings saves run without holding the interface until their
  network or persistence work finishes.
- Added interactive queues for consecutive manual mining and crafting orders.
- Reduced refresh, Production scrolling, and Galaxy Map interaction freezes by
  deferring hidden or unchanged interface models.
- Fixed Manual Control recipes, inventory choices, Manny controls, and other
  reference data disappearing after viewing or refreshing another tab.
- Added refresh and event-loop diagnostics that distinguish game-data loading
  time from interface stalls.
- Made automatic travel wait for deployed Mannys and recheck their presence
  during the cancellable preparation period.
- Added recovery travel to the reported sector of a missing owned Manny and
  displayed unavailable Manny coordinates when known.
- Made a paused automatic journey resume when its movement order becomes ready
  after mining or another blocking task finishes.
- Added the specific live hazard explanations that require a secondary travel
  acknowledgement.
- Fixed reserve tankers so their configured local mining and refueling work can
  replenish transferable Deuterium.
- Changed a completed, indefinitely retained `arrived` fleet phase to display
  as `idle` while preserving active movement states.
- Fixed switching to a traveling probe when optional local-sector autonomous
  unit telemetry is unavailable.
- Added a Galaxy Map action that opens Navigation with the selected sector's
  coordinates prefilled for operator review.
- Added a Galaxy Map filter for sectors containing a known planet with a
  habitability score of 0.5 or higher.

### Internal release support

- Preserve the full accepted dashboard for automation and safety while sending
  only the visible workspace's data across the interface boundary.
- Keep application persistence and API calls off the main interface thread.
- Keep QML models list-safe during optimistic command updates and refreshes.
- Keep navigation audio preloaded so tab changes do not rebuild the media
  player.

The internal release-support list is engineering context. Do not copy it into
public notes line by line; use `Other various fixes.` only when a final public
release genuinely benefits from acknowledging those smaller corrections.
