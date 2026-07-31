# Travel Safety and Route Intelligence

## Principle

Travel safety is advisory by default. Skunkworks calculates and explains risk,
recommends a route, and identifies when acknowledgement is prudent. The player
retains the ability to accept risk.

Setting `allowRiskyTravel` to `false` is an explicit player-owned choice that
turns travel warnings into a command-preparation blocker.

## Confirmed Game Hazards

### High-Velocity Collision

Direct movement has the following probe-destruction probabilities:

| Distance | Risk |
|---:|---:|
| 1–2 | 0% |
| 3 | 5% |
| 4 | 12% |
| 5 | 25% |
| 6+ | 40% |

The roll happens at cruise start. A SCUT corridor whose endpoints have active,
beacon-equipped relays in the same network makes collision risk zero.

### Container Detachment

For generic probes, movement break risk begins with five additional containers:
10% at five, 20% at six, and another ten percentage points per container up to
100%. Reinforced couplings move the generic threshold to ten.

The deuterium tanker threshold is two containers, or four with reinforced
couplings. One container is selected for detachment near the origin or
destination when the roll succeeds.

This risk applies once per movement. Segmenting a route avoids long-distance
collision risk but repeats the container-risk roll. Skunkworks therefore
calculates cumulative route risk rather than assuming more hops are always
safer.

### Integrity Loss

Arrival applies a deterministic roll between zero and three integrity points
per sector of movement. Skunkworks reports:

- Expected loss: 1.5% per sector.
- Maximum modeled loss: 3% per sector.
- Expected and worst-case arrival integrity.
- Fixed two-point fuel cost for every movement in a segmented route.

### Black-Hole Entrapment

Arrival in a sector containing a black hole schedules terminal entrapment.
Depending on black-hole mass, the delay is between 90 and 180 minutes. Departing
before the event cancels the trap.

### Mannies Left Behind

Mannies operating outside the probe in its departure sector become forgotten
sector objects when movement starts. Skunkworks names those Mannies in the
travel warning.

### Other Movement Conditions

- Every movement costs two deuterium points, regardless of distance.
- Sensors degrade during acceleration/deceleration and are blind in cruise.
- Movement is refused for dead, trapped, already-moving, or under-fueled probes.

The last group is handled as operational validation rather than probabilistic
risk.

## Configuration

`config/travel_safety.json` provides three presets:

- `cautious`: acknowledgement above 0% collision or container risk; 50%
  minimum arrival integrity.
- `balanced`: acknowledgement above 5% collision or 10% container risk; 30%
  minimum arrival integrity.
- `bold`: acknowledgement above 25% collision or 30% container risk; 10%
  minimum arrival integrity.
- `custom`: use only the explicit values in the file.

Individual warning toggles cover collision, containers, integrity, black holes,
forgotten Mannies, and unknown destinations. SCUT preference and risky-travel
permission are independently configurable.

## Route Comparison

The current route planner compares:

- Direct travel.
- A deterministic shortest FCC segmented route.
- Direct SCUT protection when confirmed by live network data.

Scoring accounts for probe-loss probability, cumulative container-detachment
probability, integrity loss, per-hop fuel cost, hop count, intermediate-sector
hazard knowledge, and SCUT preference. The chosen route is a recommendation,
not an irreversible restriction.

## Known Limits

- Stored sector observations can be incomplete or stale.
- Unknown destinations are reported as unknown, never silently safe.
- SCUT protection is claimed only when live network data confirms both relay
  endpoints.
- Integrity damage is deterministic on the server but cannot be predicted
  exactly without its private world seed and movement identity.
- Alternative paths beyond the deterministic shortest FCC route are future
  optimization work.
