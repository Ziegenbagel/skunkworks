# API Notes

This document records verified observations about the Von Neumann Probe API.

Only verified information should be recorded as observations.

Ideas that require additional testing should be recorded as hypotheses.

---

# Verified Observations

## Contract Baseline

Skunkworks supports deployed API v103 through upstream API v104 at revision
`e5a5f17342ec5436f1879cd16df2e9906a33e66f`.

The application checks `/api/version` before loading operational state.
Authenticated routes are rate limited to 60 requests per sliding 60-second
window, with `Retry-After` supplied on `429`.

General probe telemetry contains lightweight Manny inventory entries. The
Manny endpoints provide authoritative task state.

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
