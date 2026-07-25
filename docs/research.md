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

Architectural Impact

Skunkworks now mirrors these domains throughout the Intelligence Layer and World Model.

Aligning the application's architecture with the game's API simplifies future development and provides a stronger foundation for planning, prediction, and automation.