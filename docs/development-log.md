# Development Log

---

## 2026-07-13

### Sprint 1 — Mission Control

Completed:
- Finalized project directory structure.
- Added project documentation.
- Built the first Dashboard UI.
- Connected the dashboard to live API data.
- Refactored main.py into an application coordinator.
- Established API → UI architecture.

Current Status:
- API communication working.
- Dashboard operational.
- Live player information displayed.

Next Session:
- Populate Fleet section with live probe data.
- Create Probe model.
- Begin Current State engine.

## 2026-07-14

# Session: API Exploration & Developer Toolkit

## Accomplishments

### Mission Control
- Refactored the application to retrieve the player's probe list dynamically.
- Added support for selecting a probe by ID using `--probe-id`.
- Sector snapshots are now automatically saved for the selected probe.

### API Client
- Added `/api/probes` support.
- Updated sector requests to use `/api/probe/{probeId}/sector` instead of relying on the currently selected probe.

### Developer Toolkit

#### JSON Tree Explorer
- Improved output formatting.
- Added object type summaries for lists.
- Added representative structure output.
- Improved readability for nested collections.

#### Snapshot Compare
- Created Version 0.1.0.
- Compares semantic object counts rather than raw JSON.
- Confirms structural differences between snapshots.

## Major Discoveries

- Probe-specific sector snapshots are now supported.
- Sector snapshots appear to represent observable physical objects rather than complete operational state.
- Inventory correctly reflects onboard assets.
- Deployed Mannys do not appear to be represented as inventory items.
- Detached containers appear as sector objects.

## Next Research Goals

- Identify the endpoint responsible for active Manny operations.
- Identify endpoints for probe task state.
- Continue mapping the API before implementing automation.

## 2026-07-15

Version 0.5.0
--------------

Major Features
• Added SnapshotManager service.
• Added runtime snapshot storage.
• Added ResourceAnalyzer intelligence layer.
• Added live Fleet dashboard.
• Added live Resource Intelligence dashboard.
• Introduced shared application configuration (config.py).

Developer Tools
• JSON Tree Explorer
• Snapshot Comparison Tool
• API Explorer

Architecture
• Dashboard now consumes analyzed data rather than raw API responses.
• SnapshotManager is the single source for runtime snapshots.

Verified API Discoveries
• /api/probes provides live probe status.
• Mineable resources are exposed through
  sector.objects -> solar_system -> minableTargets.
• resourceAmounts contains remaining resources.
• resourceComposition contains resource percentages.

## 2026-07-16

## Mission 7 - Operational Intelligence

Completed:

- Added Snapshot Intelligence
- Added Inventory Intelligence
- Refactored Resource Intelligence
- Added support for persistent and dynamic mineable objects
- Added Object Inspector developer tool
- Improved dashboard organization

Major Discoveries:

- Mineable resources come from two API representations:
  - `solar_system.minableTargets`
  - `sector.objects` where `mannyMineable == true`
- Dynamic mineable objects can represent wandering resource opportunities.
- Resource Intelligence now normalizes both representations into a single internal model.