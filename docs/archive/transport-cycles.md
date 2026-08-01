# Round-Trip Transport Cycles

Round-trip transport is a durable Operation rather than an unrestricted loop.
The player selects:

- transport probe;
- resource type;
- loading/source sector;
- delivery/destination sector;
- return point;
- load-until percentage;
- unload-until percentage, including zero for completely empty;
- protected deuterium floor and contingency hops;
- repeat or single-cycle behavior.
- optional verified refueling sectors and minimum source amounts.

The cycle advances through travel to source, loading, travel to destination,
unloading, travel to the return point, and either repetition or completion.
Loading and unloading remain paused until their configured thresholds are met.

## Fuel Protection

Before an automated departure, Skunkworks reserves enough deuterium for the
complete source-to-destination-to-return-to-source loop, the configured
contingency hops, and the player's protected fuel floor. If that amount is not
available, automation pauses with `return_deuterium_reserve_unmet`.

For tanker operations, only fuel above this computed reserve is transferable.
The protected amount is visible and explainable; it is never silently offered
as delivery cargo.

At a delivery sector, an arriving tanker first searches for eligible idle
same-sector tanker probes. Tankers assigned the `deuterium_reserve` role are
filled first, allowing a stationary hub reserve to supply crafting and local
operations. Remaining deliverable fuel is then offered to the designated hub
probe and other eligible local probes. Every transfer is capped by receiver
capacity and the arriving tanker's protected return reserve.

When a cycle explicitly relies on endpoint refueling, every configured stop
must have a fresh observation of a non-depleted deuterium source meeting the
selected minimum amount. A refill-capable Manny must also be available. Missing,
stale, insufficient, or unstaffed fuel stops pause the cycle before departure.
Cycles without configured refueling stops remain fully self-fueled and reserve
the complete loop rather than assuming fuel will be available en route.

This is an automation invariant, not a claim that the game API prohibits risky
travel. Manual player choices remain available with the normal safety warning
and acknowledgement flow.
