# API Notes

This document records verified observations about the Von Neumann Probe API.

Only verified information should be recorded as observations.

Ideas that require additional testing should be recorded as hypotheses.

---

# Verified Observations

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

- Probe inventory decreases.
- A corresponding sector object may appear depending on the Manny's current state.

Additional testing is still required to determine every deployed Manny state.

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

### Mineable Resources

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

## Hypothesis 002

Wandering Deuterium asteroids are not represented in
`solar_system.minableTargets`.

Additional testing is required to determine which endpoint exposes wandering asteroids.