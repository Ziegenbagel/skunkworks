# Development Release Log

This is the private-to-development candidate ledger for the next Skunkworks
release. It is not a public release note and must never be passed directly to a
GitHub Release or packaged as `RELEASE_NOTES.md`.

Record a concise operator-visible candidate whenever behavior changes on
`develop`. At promotion time, verify each candidate against the final product,
rewrite the approved entries as bullets under the new version in
`RELEASE_NOTES.md`, then clear the promoted candidate section. Commit history
remains the record for internal implementation work.

## 1.2.0 candidates

### User-visible changes and fixes

- Added opt-in Explorer role automation with planetary-frontier preference and
  an ordinary-frontier fallback, nearest-frontier routing, verified SCUT-only
  travel, and visible campaign phase/status.
- Explorers now honor the existing fuel and Metals floors as resupply
  interrupts, automatically survey neighboring sectors on arrival, and use an
  actual idle Manny to inspect dormant constructs and derelict Others ships.
- Habitable-species and civilization contact pauses further exploration until
  the operator reviews and acknowledges the alert in Safety.
- Hardened automatic travel against leaving Mannys behind by reconciling the
  owned Manny roster with API-v128 deployed autonomous-unit observations and
  rejecting Mannys shown aboard a different probe.
- Fixed Explorers incorrectly entering an indefinite resupply wait when their
  displayed onboard Metals or fuel exactly met the configured safety floor,
  made live current-sector deposits authoritative during source selection,
  and taught resupply routing to recognize the same modern nested resource
  observations displayed on the Galaxy Map.
- Clarified Explorer frontier accounting so fleet visits—not scans or scan
  confidence—mark sectors explored; scanned-but-unvisited sectors remain valid
  destinations and are preferred over unknown candidates at equal distance.
- Stopped automatic Explorer hops from repeatedly requesting predicted-arrival
  integrity approval while live durability remains above the configured repair
  trigger, including during authoritative execution preflight; reaching the
  trigger still blocks travel until repair completes.
- Safety alerts now display the FCC sector recorded with arrivals, discoveries,
  Manny reports, and other events so operators can return after moving away.
- Explorer discovery inspection now assigns only one Manny per construct or
  derelict Others ship and resumes frontier travel after a successful order;
  failed inspection dispatches remain eligible for retry.
- Added dynamically discovered inhabited-planet messaging recipients, including
  contacts introduced by future mission and message data, plus completed Oracle access,
  including focused secondary-probe inbox synchronization. Successful Oracle
  direction-and-distance replies now place one replaceable, explicitly
  approximate Galaxy Map marker per queried player, calculated from the
  requesting probe's recorded send-time sector for future Pathfinder use.
- Corrected Oracle/contact discovery to use the focused probe's authoritative
  current-sector data and typed mission/message planet targets; API v135 does
  not expose a separate contacts route.
- Newly assembled probes now begin with zero automation targets and resource
  floors instead of inheriting the hub's policy. Settings can explicitly copy
  saved targets, priorities, and floors to another probe without copying an
  active travel destination.
- Added complete ordinary-resource Transport automation: recover matching
  drifting containers one at a time, respect each probe's upgrade-aware safe
  attachment limit, travel to the configured delivery sector, detach only the
  current circuit's cargo, and repeat with visible durable progress.
- Corrected ordinary-resource Miner automation to use its intended container
  pipeline: deploy an empty container to the asteroid, send up to four Mannys
  to mine exactly 0.25 ECE each into it, recover the confirmed full container,
  then release it to drift for Transport pickup.

### Internal release support

- For the 1.2 manual refresh, redraw the Warranty Redemption Manny schematic
  from the current in-game Manny design rather than retaining the older generic
  service diagram.
- Add a prominent manual-style liability warning explaining that Skunkworks is
  not responsible for the loss or destruction of operator probes, consistent
  with the full GPLv3 no-warranty notice.
