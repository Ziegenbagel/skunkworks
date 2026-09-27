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

Enable **Hub Supply** in Probe Role Settings. Existing production targets remain
the baseline. Enable incoming container recovery to collect raw-resource
supplies delivered by Transport; the Hub does not generate ordinary-resource
mining orders for its production shortages.

Returning Relay Placement probes request refill kits automatically. To send
other finished items, choose an owned receiver, a recipe ID, and quantity, then
queue one output batch. The receiver must rendezvous with the Hub and have
fresh storage telemetry, permanent unloading capacity, and a free attachment
slot below its safe container limit. Both probes need suitable execution modes
for their parts of the workflow.

The Hub loads a dedicated container and hands it over. The receiver unloads
into its permanent storage, waits for confirmed empty-container telemetry, and
returns the packaging to drift. It does not depart while a receipt is pending.
The Hub recovers identified returns even if general incoming-container recovery
is disabled. Larger batches use successive containers, with the previous
receipt finished before another handoff. Insufficient storage produces a hold;
it never causes supplied items to be jettisoned.

## Relay Placement

Choose one of the three sections:

1. **Automatic coverage expansion** ranks mapped star sectors inside verified
   SCUT coverage by their additional FCC coverage.
2. **Expand toward the signal** follows the approximate direction preserved in
   the game's anomaly alert. The unknown source distance is not treated as an
   exact destination.
3. **Expand in a chosen direction** uses the vector from home through the
   entered coordinates and can continue beyond that point.

Set the home sector and refill-kit size. Choose a beacon on the final usable
relay in stock, on every relay, or no beacons. The role deploys a carried relay,
activates it with an Integrated Circuit, and installs the selected beacon,
waiting for live completion at each step. Exhausted stock sends it home for Hub
resupply. A site interrupted by missing components is retained for completion.

Only mapped stars are candidates. A waiting-for-sites message means more scans
inside SCUT are needed. The workflow also holds for missing signal evidence,
unsafe travel, unavailable stock, ambiguous deployment telemetry, and storage
conflicts. Use the role status and prepared-command blockers to identify the
hold. Pausing settings preserves the current campaign for resumption.
