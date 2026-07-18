# World Model

## Overview

The World Model is the application's normalized representation of the current game state.

It is constructed by the WorldBuilder using information produced by the Intelligence Layer.

The Dashboard and future Planner consume the World Model rather than interacting directly with API responses.

---

# Current Structure

```
WorldModel
│
├── Player
│
├── Fleet
│
├── Snapshot
│
├── Probe Inventory
│
├── Sector Resources
│
└── Planner
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
Intelligence Layer
      │
      ▼
WorldBuilder
      │
      ▼
WorldModel
      │
      ├── Dashboard
      └── Planner (Future)
```

---

# Intelligence Layer

The Intelligence Layer converts raw API responses into normalized information.

Current analyzers:

- SnapshotAnalyzer
- InventoryAnalyzer
- ResourceAnalyzer
- FleetAnalyzer

Future analyzers:

- ContainerAnalyzer
- ManufacturingAnalyzer
- ConstructionAnalyzer
- RiskAnalyzer

---

# Current Responsibilities

The World Model currently provides:

- Player information
- Fleet status
- Snapshot status
- Probe inventory
- Sector resource intelligence
- Planner placeholder

---

# Future Expansion

The World Model will expand as additional systems are introduced.

Planned additions include:

- Containers
- Manufacturing
- Construction
- Knowledge references
- Operational Health
- Planner state