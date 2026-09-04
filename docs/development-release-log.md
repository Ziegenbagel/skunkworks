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

- Added multi-select item-type filters above Stored Items and Equipment so
  large inventories can be narrowed to one or several component types locally.
- Added Deuterium Engines as a maintained production target so probes can
  stockpile propulsion components for motorizing asteroids.
- Added a Communications Reports workspace with Daily Reports, Industrial
  Analysis, and a searchable Operational Archive.
- Moved automatic daily reports into local Skunkworks storage so they no longer
  consume game Logbook pages.
- Added local daily-report favorites and explicit deletion. Unfavorited daily
  reports show their retention countdown and are automatically deleted at
  17:00 local time at the end of day 30 to bound long-term storage.
- Expanded Operational Archive command cards with retained quantities,
  resources, named probes and Mannys, locations, and reasons. Daily-report
  deletion warnings appear only during their final five days. Archive search
  covers every displayed field, including those operational details and dates.
- Fixed local report deletion so the remaining daily reports stay visible
  immediately instead of returning only after a dashboard refresh.
- Made local report deletion remove its row immediately and retain the current
  list position, preventing duplicate attempts and jumps back to the newest report.
- Added selected probe-upgrade requirements to Manual Control, including each
  component or material, required quantity, stored availability, sufficiency,
  and installation time.
- Added in-application notification banners when Skunkworks is focused and the
  operating system suppresses its foreground desktop banner.
- Changed probe assembly quantities to cumulative builder targets, so moving an
  assembled probe elsewhere does not cause its original builder to replace it;
  other production quantities continue to replenish consumed or transferred stock.

- Added Normal, Low Power, and scheduled operating profiles, including daily or
  one-time start and end times. In a controlled 30-minute comparison, Low Power
  reduced average CPU usage by approximately 30% while retaining scheduled
  automation.
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
