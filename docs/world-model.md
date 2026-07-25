# World Model

## Overview

The World Model is the application's normalized representation of the current game state. It is organized around the game's primary operational domains (Fleet, Probe, Sector, and Snapshot) rather than individual user interface concepts.

It is constructed by the WorldBuilder using information produced by the Intelligence Layer.

The Dashboard and Operational Layer consume the World Model rather than interacting directly with API responses.

Higher-level reasoning is intentionally delegated to the Operational Layer, keeping the World Model focused exclusively on representing the current state of the game.

---

## Design Principle

The World Model is the application's single source of truth for live game state.

It contains normalized representations of observable game entities only.

Decision-making, planning, forecasting, and optimization are intentionally delegated to higher application layers.

---

# Current Structure

```
WorldModel
│
├── Player
│
├── Fleet
│
├── Probe
│
├── Sector
│
└── Snapshot
```

---

# Construction Flow

```
Game API
      │
      ▼
Runtime Snapshot
      │
      ▼
FleetAnalyzer
ProbeAnalyzer
SectorAnalyzer
SnapshotAnalyzer
      │
      ▼
WorldBuilder
      │
      ▼
WorldModel
      │
      ├──────────────┐
      ▼              ▼
Dashboard     Operational Layer
                     │
                     ▼
                 Planner
```

---

# Intelligence Layer

The Intelligence Layer converts raw API responses into normalized information.

Current analyzers:

- FleetAnalyzer
- ProbeAnalyzer
- SectorAnalyzer
- SnapshotAnalyzer

Future analyzers:

- ContainerAnalyzer
- ManufacturingAnalyzer
- ConstructionAnalyzer
- RiskAnalyzer

---

# Current Responsibilities

The World Model currently provides:

- Player information
- Fleet state
- Probe state
- Sector state
- Snapshot state

The World Model intentionally contains only normalized application state. Operational Services consume the World Model to answer higher-level questions without exposing raw application state to the Planner. It does not perform operational reasoning or planning.

---

# Future Expansion

The World Model will expand as additional systems are introduced.

Planned additions include:

- Galaxy state
- Exploration state
- Operational alerts
- Planner state
- Local prediction state

# Domain Model
The World Model mirrors the operational structure of the game rather than the layout of the user interface.

Current domains:

- Fleet
- Probe
- Sector
- Snapshot

This approach keeps the architecture aligned with the game's API and allows future systems, such as the Planner, Data Engine, and Automation Layer, to reason about real game entities instead of UI-specific abstractions.