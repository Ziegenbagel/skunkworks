# Development Release Log

This is the private-to-development candidate ledger for the next Skunkworks
release. It is not a public release note and must never be passed directly to a
GitHub Release or packaged as `RELEASE_NOTES.md`.

Record a concise operator-visible candidate whenever behavior changes on
`develop`. At promotion time, verify each candidate against the final product,
rewrite the approved entries as bullets under the new version in
`RELEASE_NOTES.md`, then clear the promoted candidate section. Commit history
remains the record for internal implementation work.

## 1.2.0 candidates

### User-visible changes and fixes

- Added opt-in Explorer role automation with planetary-frontier preference and
  an ordinary-frontier fallback, nearest-frontier routing, verified SCUT-only
  travel, and visible campaign phase/status.
- Explorers now honor the existing fuel and Metals floors as resupply
  interrupts, automatically survey neighboring sectors on arrival, and use an
  actual idle Manny to inspect dormant constructs and derelict Others ships.
- Habitable-species and civilization contact pauses further exploration until
  the operator reviews and acknowledges the alert in Safety.

### Internal release support

No candidates recorded yet.
