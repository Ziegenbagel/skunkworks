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

This is an automation invariant, not a claim that the game API prohibits risky
travel. Manual player choices remain available with the normal safety warning
and acknowledgement flow.
