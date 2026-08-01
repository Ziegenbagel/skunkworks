# Game Capability Architecture

## Purpose

Skunkworks exposes the public game API through domain gateways. UI, planning,
and future automation code must use these gateways instead of constructing
routes directly.

## Capability Groups

| Gateway | Reads | Controls |
|---|---|---|
| Account | Player identity | Create API keys |
| Probes | Fleet, telemetry, sectors, history, improvements, alerts, warnings, logs, SCUT | Rename, select default, move, update alerts and logs |
| Storage | Inventory and containers | Routing rules, stock moves, jettison |
| Mannies | Manny state | Every public Manny task, batch tasks, printer craft |
| Messaging | Received and sent messages | Send and mark read |
| Galaxy | Arbitrary observable sectors and fleet history | Read-only map acquisition |
| Missions | Current and historical missions | Abandon eligible missions |
| Community | Forum categories, posts, and messages | Create, edit, and delete where authorized |

Terminal mind-snapshot reassignment is exposed by `GameCapabilities`.

## Probe Targeting

Every probe-scoped gateway method requires `probe_id`. The focused probe is
selected once per application session by:

- Interactive menu in a terminal with multiple probes.
- `--select-probe`
- `--probe-id ID`
- `--probe-name NAME`
- `--default-probe`

The selected probe controls telemetry, sector snapshots, Manny state, storage,
messaging, movement, logs, alerts, and future planner recommendations.

An owned probe outside shared SCUT range remains selectable. Skunkworks builds a
limited world view from the fields the API permits and does not request
unavailable sector or Manny telemetry.

## Galaxy and Sector Maps

`SectorCoordinates` implements the game's FCC grid:

- Coordinates require even `x + y + z`.
- Every sector has twelve immediate neighbors.
- Distance is `max(abs(dx), abs(dy), abs(dz))`.

`GalaxyMap` stores:

- Fleet-wide visited-sector history.
- Per-probe visit provenance.
- Detailed or estimated observations.
- Timestamps and visit counts.

The model is intentionally persistence-neutral. A later Data Engine can store
the same records in SQLite without changing gateways, analyzers, planners, or
visualizations.

## Automation Boundary

Gateways expose game controls but do not decide when to use them. Future
automation must consume approved Planner tasks and apply safety policy,
idempotency, rate-limit scheduling, and post-action refreshes.

Community actions and irreversible controls are capabilities, not autonomous
defaults.

## Manual Inventory Operations

The Resources > Inventory & Containers workspace exposes the public game
controls for moving stock, jettisoning resources or equipment, detaching a
container into space, hiding one on an asteroid, dropping one on a planet,
recovering detached containers and drifting items, transferring deuterium to a
same-sector probe, and reassigning a Manny to another same-sector probe.

The game API supports direct whole-container transfer to another owned probe in
the same sector through the Manny `attach_to_probe` task. It does not provide a
direct arbitrary-item transfer, so individual items use the authoritative
jettison-and-salvage workflow. Hidden asteroid containers and drifting
containers can both be recovered by a Manny once their object id is known.

Manual mining orders may target the probe or a detected detached container.
When delivering to the probe, the game's container routing rules prefer a
container assigned to that resource before an unassigned container. Automated
remote mining uses the same priority: a compatible resource-designated detached
container first, then an unassigned detached container with free capacity.
Destructive and task-cancelling operations require confirmation in the UI.
