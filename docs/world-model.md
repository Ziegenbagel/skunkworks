# World Model

## Overview

The World Model is the application's normalized representation of the current game state.

It is constructed by the WorldBuilder using information produced by the Intelligence Layer.

The Dashboard and Operational Layer consume the World Model rather than interacting directly with API responses.

Higher-level reasoning is intentionally delegated to the Operational Layer, keeping the World Model focused exclusively on representing the current state of the game.

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
└── Sector Resources
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
      ├──────────────┐
      ▼              ▼
Dashboard     Operational Layer
                     │
                     ▼
             Planner (Future)
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

The World Model intentionally contains only normalized application state. It does not perform operational reasoning or planning.

---

# Future Expansion

The World Model will expand as additional systems are introduced.

Planned additions include:

- Containers
- Manufacturing state
- Construction state
- Operational health
- Additional fleet state
- Additional sector state