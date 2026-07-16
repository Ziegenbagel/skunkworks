# Skunkworks Architecture

## Overview

Skunkworks is organized into small, focused components.

Each component has a single responsibility and communicates with the next layer rather than performing multiple jobs.

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
Dashboard
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

## Intelligence Layer

The Intelligence Layer converts raw API responses into useful information.

Current modules:

- ResourceAnalyzer

Future modules:

- Fleet Intelligence
- Inventory Intelligence
- Planner Intelligence
- Forecasting

The Intelligence Layer does **not** communicate with the API or display information.

---

## Dashboard

The Dashboard presents analyzed information to the user.

Current sections:

- Player
- Fleet
- Resources
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
ResourceAnalyzer
      │
      ▼
Dashboard
```

---

# Design Principles

- Every component has one responsibility.
- Business logic belongs in the Intelligence Layer.
- User interface code only displays information.
- API communication occurs only through GameClient.
- Runtime snapshots are the application's source of truth.

---

# Future Direction

As Skunkworks grows, additional intelligence modules will be added without changing the overall architecture.

Planned additions include:

- Inventory Intelligence
- Fleet Intelligence
- Resource Forecasting
- Planner Engine
- Automation Engine