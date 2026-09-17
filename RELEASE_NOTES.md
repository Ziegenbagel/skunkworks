# Skunkworks Release Notes

## Skunkworks 1.2.0 — In Development

- Added autonomous Explorer campaigns with planetary-frontier preference and
  ordinary-frontier fallback, fleet-wide visit-based exploration tracking,
  SCUT-bound routing, and automatic fuel, Metals, and repair interruptions.
- Added guarded Explorer discovery handling for dormant constructs, derelict
  Others vessels, and habitable-species contact, including one-Manny inspection
  assignments, durable deduplication, recorded-sector alerts, and automatic
  exploration resumption after completed inspections.
- Added initial autonomous Miner role support for Deuterium-only, ordinary
  resource, and combined mining modes, configurable Manny staffing, selected
  fuel receivers, full-tank transfer logistics, and container-station grouping
  in Live Sector.
- Ensured Miner fuel transfers reserve exactly one available Manny only while
  the tank is full, use current receiver state, and leave all other available
  Mannys eligible to mine. Automatic probe repair likewise assigns only one
  Manny per repair task.
- Preserved complete Galaxy Map observations across revisits, legacy probe-ID
  formats, and filters, including previously discovered habitable planets and
  catalogued sector objects.
- Replaced probe and Manny artwork with more canonical designs, added a distinct
  large-tank Deuterium probe, and improved selected and busy-unit presentation
  in Live Sector.
- Added a SCUT transit-beacon directory beneath Manual Route Review. Operators
  can always open and center any listed beacon sector on the Galaxy Map, while
  direct beacon travel remains a separately reviewed manual-travel draft.
- Added the Salvage Probe role to the 1.2 automation roadmap for recovering
  detached containers and other items lost by fleet probes.
- Added Oracle planet messaging and per-probe conversation synchronization.
  Successful player lookups produce a named approximate Galaxy Map marker based
  on the querying probe's send-time sector, replacing that player's previous
  estimate when queried again.

## Skunkworks 1.1.4

- Added reviewed compatibility with Von Neumann Game API v135, including the
  enriched Manny missile-launch response and atomic batch missile ignition
  contract introduced by API v134–v135.

## Skunkworks 1.1.3

- Fixed generic-probe assembly planning so every missing kit component is
  manufactured at the fleet goal's priority, including atomic-printer parts,
  before lower-priority stockpile work; completed kits now proceed to assembly.
## Skunkworks 1.1.2

- Added reviewed compatibility with Von Neumann Game API v133.
- Added probe-scoped access to v131 sector-storage inventory and durable Manny
  transfers, including the dedicated external-storage Deuterium refuel route.
- Added optional explicit Manny selection for atomic-printer crafting.
- Preserved API idempotency headers alongside authentication for safe durable
  transfer retries.

## Skunkworks 1.1.1

- Fixed Windows release validation so the portable package can be published
  alongside the macOS and Linux packages.

## Skunkworks 1.1.0

- Added Normal, Low Power, Auto, and Scheduled operating profiles. Low Power
  reduced average CPU usage by approximately 30% in a controlled 30-minute
  comparison while retaining scheduled automation and urgent monitoring.
- Added opt-in desktop notifications with category and severity controls,
  restart-safe deduplication, delivery diagnostics, and queued in-app banners.
- Kept network requests, persistence work, manual commands, and settings saves
  from blocking the interface, with improved refresh and event-loop diagnostics.
- Improved large-fleet, Production, and Galaxy Map responsiveness by deferring
  hidden or unchanged interface data and reducing distant map detail when useful.
- Added a Communications Reports workspace with local Daily Reports, Industrial
  Analysis, and a detailed searchable and sortable Operational Archive.
- Added favorites, immediate deletion, and 30-day automatic retention for local
  daily reports without consuming game Logbook pages.
- Added inventory type filters, Deuterium Engine production targets, cumulative
  probe-assembly targets, and clearer assembly progress and reservation status.
- Added manual probe-upgrade requirements and an Active Probe Upgrades panel
  showing the installed upgrades reported for the focused probe.
- Improved automatic travel and missing-Manny recovery, including deployed-Manny
  checks, resumable journeys, hazard explanations, and reported recovery sectors.
- Improved reserve-tanker replenishment, focused-probe switching, Galaxy Map
  navigation handoff, and filtering for known habitable planets.
- Other various fixes.

## Skunkworks 1.0.12

- Added inspection, mining, resource detail, and Live Sector identification for
  persistent Others mothership wrecks.
- Added precise Others vessel activity and movement labels with a distinct
  spherical hostile-contact icon.
- Applied Relativistic Path Clearing to intersector integrity forecasts while
  preserving collision, container, weapon, asteroid, and black-hole risks.

## Skunkworks 1.0.11

- Added reviewed compatibility with Von Neumann Game API v130.
- Kept existing probe planet controls backward compatible with the new
  Others-only local planet harvestability field.

## Skunkworks 1.0.10

- Added reviewed compatibility with Von Neumann Game API v129.
- Kept probe sector scans on their dedicated route after the game separated
  Others-fleet scans into a new endpoint.

## Skunkworks 1.0.9
- Removed the floating autonomous-unit panel that obscured the Live Sector map.
- Retained remote owned-Manny targeting warnings, destruction countdowns,
  Galaxy Map routing, and the opt-in emergency recall response.
- Kept Live Sector unobstructed unless a critical safety takeover is required.

## Skunkworks 1.0.8

- Added critical Safety warnings when an owned Manny is targeted remotely,
  including its destruction countdown and reported FCC sector.
- Added a direct route from targeted-Manny warnings to Galaxy Map.
- Added a per-probe opt-in that recalls a clearly identified targeted Manny
  after rechecking the live warning and ownership.
- Added local autonomous-unit visibility to Live Sector.

## Skunkworks 1.0.7

- Updated missile launches to use Manny-scoped launch controls while preserving
  typed confirmation and live inventory, Manny, and target validation.
- Added support for the seven-day Manny `waiting_for_space` deadline.
- Added the latest asteroid-impact results and critical damage warnings for
  launchers, impacted probes, and Others ships.

## Skunkworks 1.0.6

- Added **Combat Control Systems** to Manual Control with explicitly confirmed
  missile launches and moving-projectile telemetry.
- Added a per-probe opt-in emergency escape to a random eligible nearby sector
  when the focused probe is targeted by a missile.
- Added missiles as production stockpile targets without authorizing automatic
  launches.
- Replaced Live Sector with a critical missile-impact countdown and a direct
  Combat Control button while the focused probe is targeted.
- Added the exact 10% integrity requirement for movement.
- Changed expired task timers to **Awaiting Server Completion**.
- Added selectable planet details, planetary resource totals, planet scanning,
  and planet mining where available.
- Added explicit mining approval for unusual artificial targets.
- Fixed depleted-asteroid grouping for previously observed sectors.
- Changed same-sector Deuterium transfers to accept direct decimal ECE amounts.
- Rounded recipe resource totals to two decimal places.

## Skunkworks 1.0.5

- Made the footer display the installed Skunkworks version consistently.
- Added Integrated Circuits to automation production targets alongside SCUT
  relays and transit beacons.
- Stopped existing safety history from appearing as a new notification after
  restarting Skunkworks.
- Condensed multiple depleted asteroids into one counted Live Sector marker.

## Skunkworks 1.0.4

- Restored sector-object inspection in Manny Field Operations.
- Kept constructs and SCUT relays available when the game reports equivalent
  object-type spellings.
- Added clear explanations when a SCUT action is missing a visible relay
  prerequisite.
- Added lightweight alert and damage-warning updates for focused secondary
  probes.
- Made newly observed alerts pulse the Safety tab until viewed.
- Added direct API-key re-entry after an authorization failure while preserving
  local history and settings.

## Skunkworks 1.0.3

- Restored verified neighbor connection lines at every settled Galaxy Map zoom
  distance.
- Added **Fit Map** to center and frame every sector admitted by current filters.
- Improved automatic camera clipping for large discovered areas.

## Skunkworks 1.0.2

- Improved Galaxy Map responsiveness during camera movement and distant views.
- Changed pan controls to follow the camera's current orientation.
- Shortened dashboard alert previews while retaining complete text in Safety.
- Fixed source installations so the `skunkworks` launcher includes required
  application modules, QML, and assets.
- Added a safe-update procedure that preserves accumulated user data.

## Skunkworks 1.0.1

- Fixed first-launch fleet loading in windowed packages without an attached
  terminal.
- Made remembered or default probe selection work normally in packaged desktop
  builds.

## Skunkworks 1.0.0

- Introduced multi-probe mission control and fleet automation for the Von
  Neumann Game.
- Added manual and automatic travel, galaxy mapping, production planning, probe
  assembly, Manny field operations, and container routing.
- Added reserve-tanker logistics, communications, logbooks, per-probe roles,
  explainable priorities, live preflight checks, execution allowlists, leases,
  and emergency stop.
- Added durable local operational history, observation deduplication, telemetry
  compaction, verified backups, and database health reporting.
- Added Observe Only as the safe starting mode and kept automatic daily Logbook
  reports opt-in.
- Released unsigned portable packages for macOS, Windows, and Linux with
  published SHA-256 checksums.
- Released Skunkworks under the GNU General Public License, version 3.
