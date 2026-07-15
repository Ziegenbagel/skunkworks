# Verified Observations

## Observation 001

Endpoint:

/api/probe/{probeId}/sector

Returns:

- Observable sector objects
- Probe inventory
- Resource stocks
- Container information

Does NOT appear to include:

- Complete operational state for deployed Mannys
- Probe task assignments

---

## Observation 002

Sector objects include:

- Solar System
- Asteroids
- Detached Containers
- SCUT Relays
- Floating Mannys

---

## Observation 003

Inventory reflects onboard assets only.

When a Manny is deployed:

- Probe inventory decreases.
- A corresponding sector object may appear depending on the Manny's state.

Further testing required.

## Hypothesis 001

The two asteroid objects returned by `/api/probe/{probeId}/sector` may represent one of two groups:

1. Persistent sector asteroids (Metal and Ice/Organic)
2. Wandering resource asteroids (currently Deuterium)

This remains unverified.

Future testing should compare object identifiers and resource compositions against known in-game objects.