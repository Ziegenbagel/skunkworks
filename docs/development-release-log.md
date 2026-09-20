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
- Ordinary-resource Miners now maintain a configurable reserve of empty
  containers, automatically crafting only the live uncovered shortage while
  respecting probe-assembly reservations and preserving an active container
  campaign when its visible role settings are edited.
- Fixed ordinary-resource Miners becoming idle when a persisted campaign
  container disappeared: they now safely select an available live empty
  container unless an active Manny task still references the prior one, and
  their role status continues to show the actual container-workflow phase when
  reserve crafting is queued or blocked.
- Deployed Miner containers now retain their campaign identity when the game
  exposes a prefixed detached-object ID or nests them under an asteroid, so
  mining begins instead of proposing duplicate deployment. Live-sector
  container markers now identify anchored versus freely drifting storage.
- Miner campaigns now reconcile an accepted deployment when the game anchors a
  different live container than the requested inventory ID, adopting that
  exact-asteroid container and beginning mining rather than replaying detach.
- Ordinary-resource Miner campaigns now continue filling all configured Manny
  worker slots after the first mining order becomes active. Production task
  details also state whether mined output is going to an anchored container,
  probe storage, or the probe's deuterium tank.
- Ordinary-resource Miners now run one durable container campaign per complete
  configured Manny group. A ten-Manny Miner with groups of four can fill two
  containers concurrently while leaving two Mannys available for crafting and
  logistics.
- Mannys outside a complete Miner group now fall back to normal target work:
  they craft when inputs allow, then may fill outstanding resource needs into
  probe storage. Campaign-group workers remain reserved through deployment and
  recovery, preventing fallback work from starving the container workflow.
- Miner container completion now accounts for accepted container-targeted
  mining orders when the game omits detached-container contents and capacity.
  Full containers are recovered after four quarter-ECE fills instead of being
  treated as empty and receiving duplicate mining orders indefinitely.
- Scoped the risk-free attached-container recovery limit to travel-heavy
  workflows that explicitly opt in. Transport loading remains protected while
  stationary Miners can recover their asteroid containers and continue cycling.
- Reused Miner containers now receive a persisted cycle-specific command
  identity, preventing valid redeployment from being cancelled as an already
  completed action. Historical accepted fills also reset when a container is
  redeployed, allowing each fresh cycle to mine normally.
- Preserved planner idempotency scopes through every task-to-command translation,
  allowing Miner redeployment cycles to produce genuinely distinct journal
  identities. Live-sector Manny logistics such as container deployment,
  recovery, and salvage now collapse matching concurrent work into one counted
  icon instead of overlapping one marker per target.

### Internal release support

- For the 1.2 manual refresh, redraw the Warranty Redemption Manny schematic
  from the current in-game Manny design rather than retaining the older generic
  service diagram.
- Add a prominent manual-style liability warning explaining that Skunkworks is
  not responsible for the loss or destruction of operator probes, consistent
  with the full GPLv3 no-warranty notice.
