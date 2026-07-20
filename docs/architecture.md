# Skunkworks Architecture

## Overview

Skunkworks is organized into small, focused components.

Each component has a single responsibility and communicates with the next layer rather than performing multiple jobs.

```
Infrastructure
    │
    ▼
GameClient
    │
    ▼
SnapshotManager
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
    ▼
Knowledge Layer
    │
    ▼
Reports
    │
    ▼
Planner (Future)
    │
    ▼
Automation (Future)
```

---

# Component Responsibilities

## GameClient

Responsible for all communication with the Von Neumann Probe API.

Responsibilities:

- Authenticate with the API
- Request player information
- Request probe information
- Request sector information

GameClient does **not** save files or interpret data.

---

## SnapshotManager

Responsible for runtime snapshots.

Responsibilities:

- Request fresh sector snapshots
- Save timestamped runtime snapshots
- Maintain `latest.json`

SnapshotManager does **not** analyze data.

---

## WorldBuilder

Responsible for constructing the application's World Model.

Responsibilities:

- Coordinate Intelligence modules.
- Assemble a normalized World Model.
- Separate construction from presentation.

WorldBuilder does **not** perform API requests or display information.

---

## Intelligence Layer

The Intelligence Layer converts raw API responses into useful information.

Current modules:

- SnapshotAnalyzer
- InventoryAnalyzer
- ResourceAnalyzer
- FleetAnalyzer

Future modules:

- ContainerAnalyzer
- ManufacturingAnalyzer
- ConstructionAnalyzer
- RiskAnalyzer

The Intelligence Layer does **not** communicate with the API or display information.

---

## Intelligence Layer Design

Analyzers interpret raw API data and return normalized information.

Analyzers should:

- Never print output.
- Never perform API requests.
- Never depend on the UI.

Analyzers may normalize multiple API representations into a single internal model.

---

## WorldModel

The World Model represents the current operational state of the game.

Current contents:

- Player
- Fleet
- Snapshot
- Probe Inventory
- Sector Resources

Future additions include:

- Containers
- Manufacturing
- Construction
- Knowledge references
- Planner state

The World Model contains normalized information and is consumed by the Dashboard and future Planner.

---

## Knowledge Layer
The Knowledge Layer provides normalized access to the game's static rules.

It interprets configuration data from gameplay.json and exposes stable interfaces that the rest of Skunkworks can consume without depending on raw game data.

Current modules:

- KnowledgeLoader
- GameplayKnowledge
- CraftingKnowledge
- ResourceKnowledge
- MovementKnowledge

Developer Toolkit

- Gameplay Explorer
- Recipe Viewer
- Dependency Viewer
- Raw Resource Viewer
- Manufacturing Report

Future modules:

- ProbeKnowledge
- MannyKnowledge
- ScanKnowledge
- ManufacturingKnowledge

The Knowledge Layer does not communicate with the API and does not represent the current game state.

## Dashboard

The Dashboard presents analyzed information to the user.

Current sections:

- Player
- Fleet
- Snapshot
- Probe Inventory
- Sector Resources
- Planner
- Alerts

The Dashboard does **not** perform business logic or API communication.

---

# Current Runtime Flow

```
Game API
      │
      ▼
GameClient
      │
      ▼
SnapshotManager
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
WorldModel ───────────────► Dashboard
      │
      ▼
Knowledge Layer ──────────► Reports
      │
      ▼
Planner (Future)
```

---

# Design Principles

- Every component has one responsibility.
- Business logic belongs in the Intelligence Layer.
- User interface code only displays information.
- API communication occurs only through GameClient.
- Runtime snapshots are the application's source of truth.
- Construction is handled exclusively by WorldBuilder.
- The World Model is the single source of truth for application state.
- Presentation consumes the World Model rather than raw API responses.
- Static game rules belong in the Knowledge Layer.
- Knowledge services expose normalized game rules rather than raw configuration data.

---

# Future Direction

As Skunkworks grows, additional intelligence modules will be added without changing the overall architecture.

Planned additions include:

- Additional Knowledge Services
- Manufacturing Planning
- Planner Engine
- Automation Engine
- Operational Health and Risk Assessment