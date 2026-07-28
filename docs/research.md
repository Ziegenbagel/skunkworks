## Open Research Items

### Probe Crafting

Status

Open

Goal

Determine the authoritative source of probe
crafting requirements.

Priority

High

Possible locations

- Gameplay configuration
- Additional config files
- API endpoint
- Game source code

Current workaround

None.

---

# Verified API Discoveries

## Probe Endpoint

Status

Verified

Endpoint

`GET /api/probe/{probeId}`

Findings

The probe endpoint is the authoritative source of probe state.

It exposes:

- Identity
- Status
- Fuel
- Inventory
- Systems
- Movement
- Navigation
- Sensor mode

Architectural Impact

Probe state should be modeled directly rather than reconstructed from sector snapshots.

---

## Sector Endpoint

Status

Verified

Endpoint

`GET /api/probe/{probeId}/sector`

Findings

The sector endpoint represents the environment currently observable by a probe.

It includes:

- Mineable resources
- Celestial bodies
- Nearby objects

It does not represent probe operational state.

---

## Relativistic Travel

Status

Verified

Endpoint

`GET /api/probe/{probeId}/sector`

Behavior

While a probe is traveling, the endpoint returns:

```
400
sensors_unavailable
```

Reason

Sensors are unavailable while traveling at relativistic speed.

Architectural Impact

Probe state and Sector state must be treated as separate application domains.

---

## Inventory Model

Status

Verified

Source

Probe endpoint

Findings

The inventory model includes:

- Capacity
- Used capacity
- Free capacity
- Resource stocks
- Containers
- External tanks
- Printers
- Mannys

Architectural Impact

The API already provides a well-structured inventory model and should be preserved with minimal normalization.

---

## Fuel Model

Status

Verified

Source

Probe endpoint

Findings

Fuel is part of the probe model.

Available information includes:

- Internal deuterium
- Maximum capacity
- External tanks
- Cargo usage
- Fill percentage

Architectural Impact

Fuel should be modeled as part of Probe rather than as an independent application domain.

---

## Systems Model

Status

Verified

Source

Probe endpoint

Findings

Systems information includes:

- Integrity
- Stored energy
- Internal clock rate
- Current task

Future Opportunities

- Health monitoring
- Maintenance planning
- Power management
- Operational alerts

---

## Movement Model

Status

Verified

Source

Probe endpoint

Findings

Movement information includes:

- Origin
- Destination
- Distance
- Fuel cost
- Departure time
- Arrival time
- Status

Future Opportunities

- ETA prediction
- Intelligent refresh scheduling
- Travel recommendations

---

## Architectural Conclusions

Status

Established

Findings

The game naturally separates into four operational domains:

- Fleet
- Probe
- Sector
- Snapshot

These domains now form the foundation of the application's World Model and Operational Layer.

Architectural Impact

Skunkworks now mirrors these domains throughout the Intelligence Layer and World Model.

Aligning the application's architecture with the game's API simplifies future development and provides a stronger foundation for planning, prediction, and automation.

## Batch Manny Tasks

Status

Open

Priority

High

Reason

New endpoint introduced:

POST /api/probe/{probeId}/mannies/tasks

Research Goals

- Request schema
- Response schema
- Supported task types
- Maximum batch size
- Partial failure behavior
- Timing information
- nextUsefulRefreshDelayMs support
- Rate limit implications

Architectural Impact

Likely becomes the primary execution mechanism for Automation.

## SCUT Relay Travel

Status

Research

Priority

High

Purpose

Determine the exact mechanics governing SCUT-assisted travel.

Research Goals

- Determine whether travel shortcuts require relays in both systems.
- Determine whether relay coverage alone is sufficient.
- Measure maximum shortcut distance.
- Determine interaction with SCUT Beacon coverage radius.
- Determine fuel savings.
- Determine travel time savings.
- Determine planner implications.

Planner Impact

SCUT mechanics will influence:

- Route planning
- Hub placement
- Relay construction priorities
- Expansion strategy
- Fuel optimization

## API Rate Limiting

Status

Verified

Limit

120 requests per minute per player

Findings

- Clients should avoid unnecessary polling.
- Many endpoints expose `nextUsefulRefreshDelayMs`.
- Refresh timing should be driven by API guidance whenever possible.
- Clients should gracefully handle HTTP 429 responses.

Architectural Impact

Skunkworks should eventually include an intelligent Refresh Scheduler that minimizes unnecessary requests while maintaining operational awareness.

## Probe Selection

Status

Verified

Finding

`GET /api/probe/{probeId}` and `GET /api/probe/{probeId}/sector` are completely independent of the currently selected probe in the web interface.

Architectural Impact

Skunkworks should manage its own focused probe rather than relying on the game's active UI selection.

## Resource Stability

Status

Research

Purpose

Determine whether resources are:

- Permanent
- Renewable
- Dynamic
- Exhaustible

Questions

- Can wandering Deuterium disappear permanently?
- What causes new wandering asteroids to spawn?
- Is there a maximum number per sector?
- Does mining affect future spawns?
- Can a sector become permanently exhausted?
- Can multiple wandering Deuterium asteroids exist simultaneously?
- Can wandering Deuterium continue spawning after existing sources are exhausted?

Planner Impact

Resource Stability will influence:

- Hub placement
- Fuel logistics
- Expansion planning
- Mining priorities
- Infrastructure investment