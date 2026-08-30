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
    ├──────────────┐
    ▼              ▼
SnapshotManager  RecipeManager
    │              │
    ▼              ▼
Runtime Snapshot  Recipe Database
    │
    ▼
Intelligence Layer
    │
    ├── FleetAnalyzer
    ├── ProbeAnalyzer
    ├── SectorAnalyzer
    └── SnapshotAnalyzer
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
                    ├── FleetService
                    ├── ProbeService
                    ├── TravelService
                    └── ManufacturingService
                    │
                    ▼
                Planner
                   │
                   ▼
     Controlled Automation Runtime
```

---

# Component Responsibilities

## GameClient

Responsible for all communication with the Von Neumann Probe API.

Responsibilities:

- Authenticate with the API
- Verify API compatibility
- Capture rate-limit metadata
- Convert rate-limit responses into typed application errors
- Request player information
- Request fleet information
- Request probe information
- Request authoritative Manny state
- Request sector information

GameClient does **not** save files or interpret data.

## API Contract Boundary

Skunkworks supports deployed API v103 through reviewed upstream API v128. The
boundary rejects older contracts and unreviewed newer contracts, preserves canonical public
identifiers, and isolates HTTP concerns from application reasoning.

New response representations are normalized by the Intelligence Layer.
Operational services and the Planner must never depend directly on API
payloads.

## Game Capabilities

`GameCapabilities` composes domain gateways for account, probe, storage, Manny,
messaging, galaxy, mission, and community features. All probe-scoped methods
require an explicit probe ID.

The gateways expose every supported game control while remaining separate from
planning and automation policy. This document is the canonical capability and
component-boundary reference.

## Probe Context

`ProbeSelector` establishes the focused probe for each session. `ProbeContext`
preserves its ID, name, model, status, default status, and reachability.

Reachable probes receive full sector, inventory, and Manny telemetry. Owned
probes outside SCUT range receive a safe limited World Model rather than falling
back silently to the default probe.

## Data Engine

The versioned SQLite Data Engine stores probe, sector, resource, visit, message,
alert, warning, and mission history. It also stores the remembered focused
probe and reconstructs the galaxy map from durable observations.

Schema version 4 adds the action journal, durable Operations, fleet roles,
event workflow state, execution leases, and the separate Skunkworks Archive.

Live API responses remain authoritative. Persistence supports historical
reasoning and never replaces live validation before a control action. See
the Data Engine section below.

---

## SnapshotManager

Responsible for runtime snapshots.

Responsibilities:

- Request fresh sector snapshots
- Save timestamped runtime snapshots
- Maintain `latest.json`

SnapshotManager does **not** analyze data.

---

## RecipeManager

Responsible for managing the game's crafting recipes.

Responsibilities:

- Load recipes from the game API.
- Normalize recipes for efficient lookup.
- Provide recipe access by ID.
- Provide a stable interface for manufacturing reasoning.

RecipeManager does **not** perform manufacturing logic or inventory analysis.

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
- FleetAnalyzer
- ProbeAnalyzer
- SectorAnalyzer
- GalaxyMapBuilder

Future modules:

- ContainerAnalyzer
- ManufacturingAnalyzer
- ConstructionAnalyzer
- RiskAnalyzer

The Intelligence Layer does **not** communicate with the API or display information.

---

## Intelligence Layer Design

Analyzers interpret raw API data and return normalized information. Each analyzer is responsible for a specific game domain (such as Fleet, Probe, or Sector) rather than individual UI concepts.

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
- Probe
- Mannies
- Sector
- Snapshot
- Galaxy map model (constructed independently until persistence is introduced)

Future additions include:

- Planner state
- Galaxy state
- Alerts
- Operational health

The World Model contains normalized information and is consumed by the Dashboard and the Operational Layer. Higher-level decision making is intentionally separated into operational services rather than accessing the World Model directly.

---

## Knowledge Layer

The Knowledge Layer provides normalized access to the game's static rules.

The Knowledge Layer provides access to game rules and reference information. Some knowledge is loaded from static configuration, while other knowledge—such as crafting recipes—is retrieved from the game API and normalized for the rest of the application.

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

---

## Operational Layer

The Operational Layer combines the live World Model with supporting game knowledge to answer operational questions.

Unlike the Intelligence Layer, Operational Services reason across multiple application layers rather than interpreting raw API responses.

Current services:

- Operations
- FleetService
- ProbeService
- TravelService
- ManufacturingService
- InventoryService
- MiningService
- GalaxyService
- TravelSafetyService
- ResourceSustainabilityService
- MessagingService, MissionService, and EventService
- ExplorationService
- PredictionService
- OperationalHealthService

Typical responsibilities include:

- Fleet operations
- Manufacturing feasibility
- Live recipe dependency analysis
- Missing resource and item ingredient analysis
- Server-faithful recursive crafting feasibility
- Fabricator and cargo-capacity constraints
- Resource availability
- Travel decisions
- Operational messaging

The Operational Layer provides the primary interface consumed by the Planner. It combines the live World Model with the Knowledge Layer to answer operational questions without exposing lower-level implementation details.

---

## Planner

The Planner evaluates the current operational state and produces an ordered queue of recommended tasks.

Rather than interacting directly with raw game data, the Planner consumes the Operational Layer, allowing planning logic to remain independent of implementation details.

Current components:

- Planner
- Desired State and production goals
- Task model
- Rule-based planning
- Priority system

## Execution Boundary

The Execution Boundary translates eligible planner tasks into typed,
contract-shaped commands. It applies probe-context validation, preflight
checks, player policy, cycle limits, and idempotency before presenting a
dry-run queue.

The controlled runtime dispatches only explicitly allowlisted typed commands
after a fresh second preflight. See `docs/planner.md` for the command pipeline.

## Safety Layer

The Safety Layer combines reviewed game rules with live hazard context. Static
fallbacks cover collision, integrity, black-hole, and model-specific container
rules. Live damage-warning rules, probe improvements, SCUT networks, inventory,
Manny locations, and stored sector observations refine each assessment.

Safety produces warnings and route comparisons. It does not silently prohibit
risk. Player profiles decide when acknowledgement is recommended and whether
risky commands should remain eligible. See `docs/logistics-and-safety.md`.

Resource Sustainability compares live deposits with durable resource history,
identifies finite or depleted sources, ranks known replacements, and emits
future hub/miner/transport role requirements. It does not assign probes or move
cargo. See `docs/logistics-and-safety.md`.

Current planning rules:

- Safety
- Idle

Future planning rules:

- Fuel
- Inventory
- Manufacturing
- Mining
- Travel
- Desired State
- Expansion

The Planner does not execute actions. It generates explainable recommendations that may later be consumed by the Automation Layer.

Desired State owns player intent and contains no planning logic. Planning rules
compare it with operational facts and emit tasks with explicit constraints.

The Planner is designed around operational constraints rather than scripted actions. It compares the current state of the fleet against the player's Desired State, identifies the constraints preventing that goal, and produces an explainable sequence of tasks to remove those constraints.

---

## Dashboard

The Dashboard presents analyzed information to the user.

Current sections:

- Player
- Fleet
- Snapshot
- Probe
- Sector
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
      ├──────────────┐
      ▼              ▼
SnapshotManager  RecipeManager
      │              │
      ▼              ▼
Runtime Snapshot  Recipe Database
      │
      ▼
Intelligence Layer
      │
      ├── FleetAnalyzer
      ├── ProbeAnalyzer
      ├── SectorAnalyzer
      └── SnapshotAnalyzer
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
          ┌──────────┴──────────┐
          ▼                     ▼
Knowledge Layer              Planner
                                │
                                ▼
                  Controlled Automation Runtime
```

---

# Design Principles

- Every component has one responsibility.
- Data interpretation belongs in the Intelligence Layer.
- Operational reasoning belongs in the Operational Layer.
- User interface code only displays information.
- API communication occurs only through GameClient.
- Live API responses are authoritative for mutable state.
- Runtime snapshots preserve observable sector history and diagnostics.
- Construction is handled exclusively by WorldBuilder.
- The World Model is the single source of truth for application state.
- Presentation consumes the World Model rather than raw API responses.
- Static game rules belong in the Knowledge Layer.
- Operational reasoning belongs in the Operational Layer.
- Knowledge services expose normalized game rules rather than raw configuration data.
- Operational services consume the World Model rather than raw API responses.
- The World Model represents game entities rather than UI concepts.
- Probe and Sector are the primary operational domains.
- The Planner consumes Operational Services rather than raw application state.
- Planning logic is organized into independent rule modules with a single responsibility.
- Live game data is preferred over duplicated local data whenever the API provides it.
- Canonical API identifiers are preserved across internal layers.
- Static knowledge records its upstream version and is synchronized before
  planning logic depends on it.
- Planner tasks represent real API actions. Explanatory dependency nodes are
  not executable actions unless the API exposes them as such.
- Normalize data only when it provides meaningful operational value.
- Managers own data lifecycle; services own operational reasoning.
- The Planner asks questions; services answer them.

---

## Explainable Planning

Every recommendation produced by the Planner should be traceable.

The Planner should explain:

- What it recommends.
- Why it recommends it.
- Which operational constraints led to that recommendation.

Operational services answer domain-specific questions, while the Planner combines those answers into an explainable task queue.

---

# Future Direction

As Skunkworks grows, additional intelligence modules will be added without changing the overall architecture.

Planned additions include:

## Planned Intelligence

- Additional Knowledge Services
- Data Engine
- Prediction Engine

## Planned Planning

- Planner expansion
- Desired State
- Constraint Solver
- Goal decomposition

## Planned Automation

- Refresh Scheduler
- Mission Control
- Automation Engine
- Operational Health and Risk Assessment
