# Resource Sustainability and Fleet Logistics

## Confirmed Generation Rules

The reviewed universe generator creates wandering-asteroid fields
deterministically:

- A wandering field contains between one and five asteroids.
- A black-hole region has a 55% chance to receive a one-to-five wandering
  asteroid field.
- Stellar-system asteroid belts are separate and contain at most four belts.
- Mining subtracts resources from the persistent asteroid object.
- Exhausted resource amounts remain at zero.
- No asteroid replenishment or replacement-spawn path was found.

“Five wandering asteroids” is therefore a generation maximum for a wandering
field, not a renewable population cap.

## Warning Model

`config/resource_safety.json` controls:

- Low-resource warnings.
- Finite-field notices.
- Low and critical remaining percentages.
- Absolute minimum-resource threshold.
- Minimum replacement-deposit size.
- Number of replacement candidates.
- Logistics-blueprint generation.

Current remaining amounts are compared with the highest amount Skunkworks has
observed for the same object, sector, and resource type. This makes depletion
warnings improve naturally as history accumulates.

Defaults:

- Low: 25% remaining.
- Critical: 10% remaining.
- Absolute warning floor: 0.25 ECE.
- Replacement candidate minimum: 1 ECE.

## Replacement Sources

The Data Engine selects the newest observation for every known deposit. Sources
whose newest amount is below the replacement minimum are excluded, even if an
older observation showed abundant resources.

Candidates are ranked by:

1. FCC distance from the hub.
2. Remaining observed amount.
3. Stable sector coordinates.

Historical candidates are recommendations only. Live observation and travel
safety must be refreshed before deployment.

## Logistics Blueprint

When a low resource has a known replacement source, Skunkworks creates a future
fleet-role plan:

- `hub`: stays in the production system and receives material.
- `miner`: remains in the replacement sector and operates the deposit.
- `transport`: shuttles material from source to hub.

These are planning roles, not current API commands. Fleet assignment, storage
transfer, route scheduling, capacity selection, and delivery cycles remain part
of the future logistics automation runtime.

## Known Limits

- A source observed only after substantial mining has an incomplete baseline.
- A stale positive observation may remain a candidate until a newer scan
  records its depletion.
- Resource demand rate and estimated time-to-exhaustion require additional
  timestamped observations.
- Persistent stellar-system mineable targets and wandering asteroids follow
  different generation limits.
