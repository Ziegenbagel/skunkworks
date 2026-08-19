# API Notes

This document records verified observations about the Von Neumann Probe API.

Only verified information should be recorded as observations.

Ideas that require additional testing should be recorded as hypotheses.

---

# Verified Observations

## Contract Baseline

Skunkworks supports deployed API v103 through upstream API v112, verified
against the live contract on 2026-08-19.

The application checks `/api/version` before loading operational state.
Authenticated routes are rate limited to 60 requests per sliding 60-second
window, with `Retry-After` supplied on `429`.

General probe telemetry contains lightweight Manny inventory entries. The
Manny endpoints provide authoritative task state.

API v105 adds `DELETE /api/probe/{probeId}/move`. It succeeds only during
movement preparation, cancels the scheduled movement and container-damage
events, restores the probe to idle, removes synthetic forgotten-Manny objects,
and refunds the full reserved movement deuterium.

API v106 represents Manny mining as one terminal scheduled task. While mining
is active, `extractedAmount` and `depositedAmount` remain zero even though
`taskProgressPercent` and `taskEstimatedEndTime` advance. At the final deadline,
capacity is checked and extraction plus delivery commit atomically. Clients
should use the task progress/deadline—not intermediate deposit counters—for
active-state progress.

Crafting now reserves its output container and volume when work starts. Those
reservations are included in storage-capacity calculations until the scheduler
replaces them with the completed output.

As of the 2026-08-02 game update, container detach and planet-drop operations
reject a container whose space is reserved for active crafting output with HTTP
409 and business code `storage_container_reserved`. If a reservation becomes
invalid before completion, the game terminates the Manny task, releases the
reservation, and preserves `invalid_cargo_reservation` as the failure reason.
Manny list and detail responses also expose nullable ISO 8601 `taskStartTime`.

API v108–v111 add persistent motorized asteroids. The Manny gateway accepts
`motorize-asteroid` and `refuel-motorized-asteroid`; the probe gateway can
launch `system_impact` or `sector_transfer` trajectories and request locally
detectable trajectory telemetry. Detailed sector objects are allowed to expose
`motorized`, binary `motorFuelStatus`, and embedded `trajectory` data. API v109
also marks improvements with `installableOnProbe`, so asteroid-only blueprints
can remain separate from probe upgrades.

API v112 adds probe-scoped deletion for both persistent alerts and damage
warnings. Skunkworks exposes both operations through the probe gateway while
retaining the existing ownership boundary enforced by the game.

## Observation 001

### Endpoint

`/api/probe/{probeId}/sector`

### Purpose

Returns a complete snapshot of the selected probe's current observable world.

### Verified Contents

- Observable sector objects
- Probe inventory
- Resource stocks
- Container information
- Scan information
- Nearby owned probes
- SCUT network information

### Does Not Include

- Complete operational state for deployed Mannys
- Probe task assignments

---

## Observation 002

### Sector Objects

Verified persistent object types include:

- Solar System
- Asteroids
- Detached Containers
- SCUT Relays
- Floating Mannys

The Solar System object contains additional navigation and mining information.

---

## Observation 003

### Inventory

Inventory reflects onboard assets only.

When a Manny is deployed:

- Probe inventory decreases. Deploying a Manny removes it from onboard inventory and changes how it is represented in sector data.
- A corresponding sector object may appear depending on the Manny's current state.

Behavior not yet fully characterized.

---

## Observation 004

### Endpoint

`/api/probes`

### Purpose

Returns the player's complete probe list.

### Verified Fields

- id
- name
- status
- isDefault

### Verified Behavior

The status field is live and updates as probes change state.

Observed values include:

- idle
- cruising
- decelerating

This endpoint does not appear to include probe fuel information.

---

## Observation 005

### Persistent Mineable Resources

Mineable resource information is located under:

`sector -> objects -> solar_system -> minableTargets`

Each mineable target exposes:

- resourceAmounts
- resourceComposition

### resourceAmounts

Represents the remaining mineable resources.

### resourceComposition

Represents the composition percentages for each resource type.

This information is now used by the ResourceAnalyzer.

---

# Active Hypotheses

## Hypothesis 001

The two asteroid objects returned by
`/api/probe/{probeId}/sector`
represent the persistent sector asteroids:

- Metal Asteroid
- Ice / Organic Asteroid

Current testing supports this hypothesis.

---

## Observation 008

Dynamic mineable resources appear directly under:

sector.objects

Objects with

mannyMineable == true

represent resources that can currently be mined but are not part of the persistent solar system resource list.

## Observation 006

Mineable resources are exposed through two mechanisms:

### Persistent Resources

Located under:

/api/probe/{probeId}/sector

↓

sector.objects

↓

solar_system.minableTargets

### Dynamic Mineable Resources

Located directly in:

sector.objects

Objects become mineable when:

mannyMineable == true

Both representations expose:

- resources
- resourceAmounts
- resourceComposition

Resource Intelligence normalizes both into a common internal model.

## Observation 007

### Endpoint

`/api/crafting-recipes`

### Purpose

Returns the complete crafting database maintained by the game server.

### Verified Contents

Each recipe includes:

- id
- name
- description
- craftableBy
- ingredients
- durationSeconds
- output

### Verified Behavior

The API serves as the authoritative source for crafting recipes.

Skunkworks uses this endpoint to populate RecipeManager at startup rather than maintaining a local recipe database.

## Observation 009

### Recursive Crafting

A craft request represents one final-output order. The server consumes existing
components first, recursively synthesizes missing craftable components inside
that order, and adds their durations to the task.

Dependency trees in Skunkworks are explanatory rather than separate executable
craft orders. Crafting deuterium comes from `probe.fuel.deuterium`, not
`inventory.resourceStocks`.

## Observation 010

### Canonical Public Values

- Stored material: `carbon_compounds`
- Movement phase: `cruising`
- Probe models: `generic`, `deuterium_tanker`
- External tanks: `inventory.externalTanks`
- Movement fuel cost: 2 deuterium points per trip

## Observation 011

### Deuterium Tanker Probe

The `deuterium_tanker` is a probe model assembled through the Manny
`assemble-probe` action. It is not a normal entry in the crafting-recipe
catalog.

Assembly takes three hours and consumes the generic probe components plus:

- 10 steel plates
- 2 linear actuators
- 1 integrated circuit
- 2 selected, distinct, empty additional containers

The completed tanker has:

- 400 maximum deuterium by default
- 800 maximum deuterium with the deuterium-compression improvement
- the same fixed movement fuel cost as other probes
- container-detachment risk beginning at 2 additional containers, or 4 with
  reinforced container couplings

`transfer-deuterium-to-probe` starts a five-minute Manny task. The source and
target owned probes must be in the same sector, the Manny must be onboard and
available, and the requested amount must be strictly lower than the source
reserve. The target fills only to its maximum and surplus returns to the
source.

This makes tanker probes mobile fuel carriers, but not detached deuterium
storage containers. Fuel logistics require rendezvous between probes.

## Observation 012

### API v107 manual-control coverage audit

The public v107 OpenAPI contract was compared against the application gateways,
service allowlists, and operator-facing controls. A route existing in a gateway
does not count as supported unless an operator can discover it and submit its
required payload through an appropriate review flow.

The Manual Control inventory workspace now exposes the previously unreachable
Manny operations:

- `inspect-sector-object` for asteroids, detached containers, and dormant constructs
- `install-bookmark` for current-sector celestial objects
- `drop-manny-cargo` only for a Manny reported as `waiting_for_space`
- `refill-deuterium-tank` when a current-sector refuel station is observed
- `turn-on-relay` for an inactive current-sector SCUT relay
- `install-scut-transit-beacon` for an active relay without a beacon

The complete relay workflow is now visible in one place: jettison a specific
stored `scut_relay`, refresh the sector observation, activate that relay with an
idle Manny and an integrated circuit, then install a stored transit beacon.
Relay ids remain opaque strings in sector telemetry and are converted to the
integer `relayId` required by the two task endpoints only at command submission.

Existing UI coverage was confirmed for movement and cancellation, scanning,
crafting and printer crafting, mining, repair and improvements, Manny recall,
storage moves and rules, container detach/drop/recovery, item and resource
jettison, same-sector transfers, reservation reassignment, alerts, logbooks,
messages, missions, and probe renaming.

The following operations remain outside the general inventory panel because
their dedicated controls require stronger context and confirmation:

- `assemble-probe` is in Manual Control / Crafting. It requires an idle Manny,
  a model, and two distinct empty additional containers, and presents the full
  destructive assembly warning before submission.
- setting `isDefault` is in Fleet identity controls and is enabled only for a
  reachable, focused, non-default probe. The confirmation states the shared
  SCUT/same-sector requirement.
- `mind-snapshot/reassign` is in Safety. It appears only when the current
  default probe is reported dead or trapped by a black hole and explicitly
  warns that the terminal state is deleted and the reference frame reset.
- batch Manny task endpoints are transport optimizations, not separate player
  features; Skunkworks uses the equivalent reviewed individual actions.
- account-key and forum administration are account/community concerns rather
  than focused-probe manual controls.

### Compatibility Note

The tanker assembly details were added while the public API still identified
itself as v104. API-version acceptance alone therefore cannot prove schema
compatibility. Skunkworks should also validate required fields, models, task
routes, and request shapes at startup.
