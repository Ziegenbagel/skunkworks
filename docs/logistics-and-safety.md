# Logistics and Safety

This is the canonical reference for travel risk, resource sustainability,
containers, mining depots, and repeated transport. The safety layer warns and
requires acknowledgement according to policy; it does not silently forbid an
operator from accepting an allowed risk.

## Travel invariants

- Validate FCC parity, distance, fuel cost, return reserve, probe state, and
  current observations immediately before dispatch.
- Warn about collision/destruction probability, container detachment,
  integrity loss, black holes, and Mannies left behind.
- A verified SCUT transit-beacon corridor removes movement-destruction risk,
  but does not remove container-detachment risk.
- API v105 movement cancellation is available only during preparation and
  refunds reserved deuterium.

## Resource invariants

- Track probe storage, attached containers, detached containers, asteroid
  reserves, source freshness, and resources allocated to higher-priority work.
- Warn before a persistent source falls below its configured reserve and when
  a system approaches its five-wandering-asteroid generation limit.
- Never count an active craft output as missing, reuse its reserved container
  capacity, or spend resources already claimed by a higher-priority goal.
- API v106 mining commits extraction and deposit atomically at its terminal
  deadline; active zero deposit is not evidence of a stalled Manny.

## Container and depot policy

Automatic mining prefers an attached container assigned to the requested
resource, then an eligible unassigned container. Operators retain manual control
over transfer, jettison, deployment, recovery, and mining destination.

A depot comprises an asteroid/source, assigned miners, deployed storage, and
collection policy. Full containers may be recovered and replaced with empty
ones; low-source warnings should propose replacement mining sectors and
transport capacity.

## Round-trip transport

A durable cycle records the probe, loading sector, unloading sector, return
point, resource, load/unload thresholds, protected-deuterium floor, contingency
hops, optional verified refuel stop, and repeat policy.

Before every leg Skunkworks refreshes the route and safety context. A tanker
delivering deuterium to a hub fills a designated stationary tanker before a
generic probe when policy requests buffer-first delivery. A route must never
depend on refuelling at a sector without a currently verified source.

## Safety profiles

Profiles tune warning and acknowledgement thresholds. They do not bypass the
emergency stop, stale-data rejection, API compatibility boundary, command
allowlist, or final preflight.
