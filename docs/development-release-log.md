# Development Release Log

- Replace the unfinished Builder Support role with Missile Destroyer and add
  testable Salvage campaigns. Destroyers require explicit combat consent and
  a sector mission, reconcile one missile at a time, return to their selected
  Hub for resupply, and await the next mission. Salvagers protect claimed cargo,
  recover eligible observed objects and deliver their recovered cargo to a Hub.
  Both roles preserve saved goals while suppressing unrelated industrial work.

- Send available Hub package supplies without waiting for missing crafts to
  fill a container. Preserve remaining quantities for subsequent shipments.
  Bound accepted crafts by the cycle's initial shortage so delayed telemetry
  cannot produce seven containers when only two are needed.

- Add Mannys and additional containers to Hub package selection. Craft extra
  assets while preserving existing Hub counts, then transfer them permanently
  with storage, idle-worker, safe-container, and accepted-command checks.

- Unblock Hub receivers whose temporary delivery containers hold incidental
  Mannys or raw resources. Safely relocate that cargo to permanent storage
  before returning packaging and releasing the departure hold.

- Require automatic, signal-source, and coordinate-directed relay expansion to
  place at the combined active SCUT coverage boundary. Recheck unbuilt targets
  and deployment preflight; wait for mapped frontier stars instead of falling
  back to overlapping interior placements.

- Load QML icons asynchronously so slow image reads cannot block startup or
  rebuilding sector/map markers on the GUI thread.

- Bound dashboard command-history reads before formatting, preserve complete
  industrial totals using SQL aggregation, and use indexed assembly-only reads
  for cumulative fleet goals. Prevent accumulated journal history from making
  every refresh and planning pass repeatedly process all prior commands.

- Prioritize pending Hub packages ahead of routine bulk production, retain role
  goals during mining fallback, and avoid cancelling valid bounded mining orders
  for changed deficit estimates. Expansion probes prepare their next kit while
  away and reuse that request for refill; preparation alone never permits handoff.

- Stop automatic dispatch after an accepted movement command so stale local
  work cannot send Mannys mining after departure. Active Manny task cards now
  show their sector and remote SCUT visibility; remote workers no longer appear
  beside the probe in Live Sector.

- Hub packages automatically clear unrelated items, resources and stored Mannys
  into other available Hub storage before packing. Cleanup preserves cargo,
  avoids other packages' containers, and waits when cargo is busy or storage
  space is unavailable.

- Hub deliveries may temporarily exceed a stationary receiver's travel container
  limit when each item fits its permanent storage. Receipts still block travel
  until unloading and empty-container return are confirmed. Expansion probes
  preserve their own empty storage during refills.

- Supply Queue now separates packages into readable cards with larger recipient
  headings, aligned component counts, distinct next-step and handoff messages,
  and expandable container details.

- Fixed Hub handoff checks using stale fleet positions and base container limits
  for upgraded receivers. Packages can be packed before rendezvous. Each queue
  entry now separates loaded/available/crafting/missing components, shipment and
  container identity, and receiver location/capacity blockers.

- Fixed Hub Supply suppressing local mining for resource reserves, ordinary
  crafting, and queued packages. Hubs now retain the shared planner's mining
  orders alongside incoming container deliveries.

- Hub Supply now keeps multiple automatic refill and manual package requests,
  prepares stock while receivers wait, and advances ready recipients independently.
  The package editor offers component dropdowns, quantities, and additional rows.
  Larger packages ship across successive containers; each receiver still unloads
  and returns its temporary container before another handoff. Integral decimal
  receiver IDs and expired receiver readiness no longer strand valid requests.

- Fixed ordinary-resource Miner deployments starting without a complete idle
  crew and a cycle limit that staggered quarter-container orders across several
  automation cycles. SCUT Network Expansion now explains when Hub resupply is
  blocked because the receiving probe has no safe delivery-container slot, and
  returns a confirmed-empty container automatically when one is available.

- Added **Prepare and Install** for a selected probe upgrade. Skunkworks mines
  and crafts missing inputs, protects required stock from competing automation,
  and installs when ready. Goals survive restarts and can be cancelled without
  cancelling already accepted game tasks.

- Added the missing one-time approval control for queued automation commands.
  Require Approval orders and commands excluded from the Automatic allowlist
  can now be approved individually without changing the saved allowlist, while
  still receiving fresh safety, reservation, risk, and live-state checks.

- Fixed relay activation and SCUT transit-beacon installation failing when Qt
  represented the game's integer relay identifier as an integral decimal such
  as `805.0`; both commands now validate and normalize the identifier before
  sending the Manny task.

- Fixed automatic Explorer travel consuming the configured fuel safety floor.
  Planning now refuels the next leg above the protected arrival reserve, and
  live move preflight rejects any departure that would cross that floor.
  Explorers at the boundary now redirect to the nearest known SCUT-covered
  Deuterium source affordable with their remaining fuel, or pause and issue a
  critical manual-refueling notification when no source is reachable.

- Fixed ordinary-resource Miners retaining recovered full containers aboard.
  Containers reported only through resource-stock placements are now
  normalized as attached inventory, allowing the campaign to detach them for
  Transport pickup instead of abandoning their persisted release phase. The
  Miner also drains full matching containers stranded by older campaign state.

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
- Travel safety now recognizes the canonical `reinforced_couplings` improvement
  ID as well as the historical longer alias, preventing upgraded tanker probes
  from being evaluated with the unreinforced container-detachment threshold.
  Container-risk prompts now also report the observed attached-container count,
  the first risky count, and the risk-free maximum.
- Probe target/floor copying now labels the focused probe as the source and the
  selected probe as the overwritten destination, requires a named directional
  confirmation, and repeats that source → destination direction on completion.
- Settings now includes an attached-container travel-safety comparison for
  generic and tanker models with and without Reinforced Couplings, showing the
  risk-free additional count, first risky count, and total risk-free storage.
- Resource reserve targets now accept, display, persist, and plan in 0.1 ECE
  increments instead of forcing whole-number quantities.
- Miner role settings now present mutually exclusive Deuterium Mining and
  Other-Resource Mining workflows. Each mode shows only its relevant controls;
  combined mode is no longer accepted, and ordinary mining requires at least
  one selected resource.

### Internal release support

- For the 1.2 manual refresh, redraw the Warranty Redemption Manny schematic
  from the current in-game Manny design rather than retaining the older generic
  service diagram.
- Add a prominent manual-style liability warning explaining that Skunkworks is
  not responsible for the loss or destruction of operator probes, consistent
  with the full GPLv3 no-warranty notice.
