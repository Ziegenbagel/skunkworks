# Capability Matrix

This is the release-level map of exposed controls. Detailed behavior remains in
the Operator Manual, architecture, API notes, planner, and safety references.

| Area | Observe | Manual control | Automated control | Principal safety boundary |
|---|---|---|---|---|
| Fleet and probes | Yes | Rename, focus, role assignment, Manny naming | Role-aware planning | Explicit probe identity and reachability |
| Galaxy and sectors | Yes | Scan and inspect | Bounded refresh and history | Live API remains authoritative |
| Travel | Yes | Preview and send route | Durable segmented travel goals | Fuel, hazards, collision-safe segments, allowlist |
| Production | Yes | Craft and assemble | Priority manufacturing and dependency mining | Next-unit reservation and live preflight |
| Manny operations | Owned fleet plus v128 local deployed-unit observations | Mine, repair, transfer, deploy/recover | Goal and floor-driven dispatch; opt-in targeted-Manny recall | Idle/ready state, bounded claims, live alert identity, capacity |
| Cargo and containers | Yes | Move, jettison, recover, route | Routing rules and logistics goals | Reservation, destination, and capacity validation |
| Deuterium logistics | Yes | Transfer and refuel | Tanker and reserve chains | Full-loop fuel and protected reserve |
| SCUT/network operations | Yes | Relay/beacon workflow and blueprint share | No general autonomous network construction | Capability, inventory, and network checks |
| Motorized asteroids | Yes where API exposes it | Install, refuel, launch, sculpt | No | High-impact confirmation and capability locks |
| Combat systems | Projectile, probe-target, and remote Manny laser alerts/countdowns | Typed-confirm missile launch | Missile crafting; separate per-probe escape and Manny-recall opt-ins | Fresh target identity, one dispatch, emergency stop, 10% movement integrity floor |
| Communications | Yes | Messages and logbook editing | Optional daily role reports | Explicit recipient/page and API validation |
| Safety and policy | Yes | Configure and acknowledge | Preflight, leases, allowlists, emergency stop | Policy never replaces live validation |

Reviewed compatibility is API v103 through v128. A newer unreviewed server
version is visibly identified and continues only under the forward-compatible
contract boundary. Endpoint-level
evidence and unresolved upstream behavior are maintained in `docs/api-notes.md`.
