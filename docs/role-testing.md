# Testing the 1.2 fleet roles

These workflows are development features. Start with Observe or Approve mode,
inspect the prepared commands, and enable live Automatic mode on participating
probes when ready. STOP and normal travel checks still apply.

## Ordinary-resource Miner

Choose **Other-Resource Mining**, select local resources, and enable the role.
Each deployed container reserves four named Mannys. Its first fill waits until
all four are ready. Each worker receives one 0.25-ECE order, and one member of
that same crew recovers the full container before it is released for Transport.
Extra unassigned Mannys can craft or work on other goals. A partial reserved
crew visibly waits instead of trickling miners into the campaign.

## Hub

If unrelated cargo enters a reserved delivery container, the Hub should show
**clearing container**, move it to other unreserved onboard storage, and resume
packing after the move appears in inventory. Check a stored Manny as well as
an ordinary item or resource. The transfer actor must differ from a moved
Manny. Full destination storage or busy cargo must wait without discarding
anything or handing off mixed contents.

The supply queue separates preparation from handoff. Each package shows items
still to craft, active crafting, available stock allocated to that package,
observed loaded cargo and its container. A packed shipment may wait for a
receiver; that wait must not prevent packing. Verify an upgraded receiver uses
its own safe maximum and that fresh arrival telemetry overrides an old fleet
position. The handoff line reports the actual container count and safe maximum;
a receiver at or above the maximum may accept one temporary delivery while
stationary, provided all cargo fits its own individual storage slots. Verify
departure remains blocked until the delivery container is unloaded and returned.

Choose a recipient, click **Add Component**, select a component and quantity,
and add more rows as needed. **Queue Package** appends a separate request; repeat
for another recipient. The evaluated supply queue includes automatic SCUT
refills and shows each recipient's remaining items and waiting/loading status.
Verify a waiting recipient does not prevent production or another recipient's
shipment. A package larger than one container must retain its remaining items
after an accepted handoff, then wait for unloading/empty-container return before
the next shipment to that receiver. Requests and shipment progress survive a
restart. Enable each expansion role to generate its automatic refill requests.

Enable **Hub Supply** in Probe Role Settings. Existing production targets remain
the baseline. Enable incoming container recovery to collect raw-resource
supplies delivered by Transport. The Hub also mines local resources for its
configured reserves and crafting shortages using the normal planner and safety
checks. Check a depleted Metals reserve and a blocked craft with a mineable
local deposit: both should produce mining work when workers and storage permit.

Returning SCUT Network Expansion probes request refill kits automatically. To send
other finished items, choose an owned receiver, select components and quantities,
then queue a package. The receiver must rendezvous with the Hub and have
fresh storage telemetry and permanent unloading capacity. The travel container
limit does not block a temporary stationary delivery. Both probes need suitable execution modes
for their parts of the workflow.

The Hub loads a dedicated container and hands it over. The receiver unloads
into its permanent storage, waits for confirmed empty-container telemetry, and
returns the packaging to drift. It does not depart while a receipt is pending.
The Hub recovers identified returns even if general incoming-container recovery
is disabled. Larger batches use successive containers, with the previous
receipt finished before another handoff. Insufficient storage produces a hold;
it never causes supplied items to be jettisoned.

## SCUT Network Expansion

Choose one of the three sections:

1. **Automatic coverage expansion** ranks mapped star sectors inside verified
   SCUT coverage by their additional FCC coverage.
2. **Expand toward the signal** follows the approximate direction preserved in
   the game's anomaly alert. The unknown source distance is not treated as an
   exact destination.
3. **Expand in a chosen direction** uses the vector from home through the
   entered coordinates and can continue beyond that point.

Set the home sector and relay refill target. One Integrated Circuit per relay
is included automatically. Optionally enable beacon refills and choose a separate
beacon stock target; the Hub supplies only the missing quantities. Changes apply
to the next refill request; an existing delivery finishes its queued batch. With beacon
refills disabled, depleted beacons hold the probe at home if placement still
requires them. Choose a beacon on the final usable
relay in stock, on every relay, or no beacons. The role deploys a carried relay,
activates it with an Integrated Circuit, and installs the selected beacon,
waiting for live completion at each step. Exhausted stock sends it home for Hub
resupply. A site interrupted by missing components is retained for completion.

Only mapped stars are candidates. A waiting-for-sites message means more scans
inside SCUT are needed. The workflow also holds for missing signal evidence,
unsafe travel, unavailable stock, ambiguous deployment telemetry, and storage
conflicts. Use the role status and prepared-command blockers to identify the
hold. Pausing settings preserves the current campaign for resumption.
