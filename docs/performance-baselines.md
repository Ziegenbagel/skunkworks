# Performance Baselines

These measurements are local reference points, not universal hardware
requirements. Re-run `python -m tools.performance_probe` against a copied or
test database when changing persistence, galaxy reconstruction, or compaction.

## 1.1 testing slice — 2026-08-25

- Platform: macOS arm64 development machine
- Database: accumulated private test profile
- Database size: 279,670,784 bytes
- Retained rows: 1,029,940 resource observations; 63,708 probe snapshots;
  23,290 action journal entries; 1,991 sector observations; 263 visited sectors
- Database report: 11.63–12.05 ms (median 11.84 ms, three samples)
- Cold galaxy reconstruction: 203.24–226.09 ms (median 217.75 ms, three samples)
- SQLite integrity check: 225.06–912.18 ms (median 231.95 ms, three samples)
- Reclaimable space: 0 bytes

Command:

```shell
SKUNKWORKS_HOME="$PWD/private/test-data" \
  uv run --no-sync python -m tools.performance_probe --repetitions 3
```

The first phases also retain automated structural checks for lazy heavy tabs,
local production countdowns, interaction-only galaxy simplification, settled
overlay restoration, view-relative pan, and fit-all-visible behavior. Startup,
live API refresh, probe switching, and interactive frame-time comparisons must
be captured during private testing because they depend on game-service latency
and a real graphics surface.

## 1.2 refresh regression — 2026-10-09

Offline measurements on a SQLite backup of the private development database
(138,706 action rows), using the same machine and Python environment:

| Operation | Before | After |
| --- | ---: | ---: |
| Reports/archive projection | 12.417 s | 0.325 s |
| One cumulative assembly count | 5.824 s | 0.001 s |

These are single local samples, not end-to-end refresh timings or API latency
measurements. The projection benchmark uses `MissionControlViewModelBuilder._reports()`
with the copied DataEngine and a minimal world (focused probe 644, empty fleet
and Manny maps). The assembly benchmark calls `recorded_probe_assembly_count`
for that probe's generic model. No live game requests are made. The repair
limits command details in SQL, aggregates complete industrial totals, and indexes
filtered successful-assembly queries. Full live/UI refresh timing remains to
be verified in the running application.
