# Public Screenshot Privacy Review

Status: APPROVED SYNTHETIC DATA

The public manual uses repository-owned captures of the real Skunkworks QML
running against a fictional, offline documentation profile. The capture process
does not connect to the game API, read the operator database, or access the
operating-system credential vault.

Verification completed for the 1.0 preparation build:

1. Captures use fictional probes such as Wayfarer Hub, Peregrine Explorer,
   Lantern Fuel Tender, and Harbor Fuel Reserve.
2. Manny names, object IDs, coordinates, messages, quantities, missions,
   logbook entries, and timestamps are synthetic.
3. Source captures live in `assets/synthetic-screenshots/` and are reproducible
   with `tools/capture_synthetic_manual.py`.
4. The DOCX and PDF are rebuilt from those assets and visually inspected after
   any manual or screenshot change.

The original operator-supplied screenshots remain private development inputs and
are not referenced by the public manual builder.
