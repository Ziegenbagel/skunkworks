# Skunkworks

> **Configure your fleet. Define your objectives. Let Skunkworks handle the rest.**

Skunkworks is an autonomous operations manager for the **Von Neumann Probe** game.

Skunkworks is designed around layered architecture and explainable planning. Rather than hardcoding gameplay sequences, it models the current state of the game, reasons about desired outcomes, and generates understandable operational plans that can eventually be automated.

Instead of manually managing repetitive tasks, Skunkworks continuously monitors your fleet, compares the current state against your desired state, and intelligently plans the work needed to achieve your objectives.

Its goal is simple:

> **When you sit down to play, your fleet should already be prepared. Skunkworks doesn't replace strategic decision-making—it eliminates repetitive operational work so the player can focus on exploration and long-term planning.**

---

# Mission

Players should focus on exploration, expansion, and strategy.

Skunkworks focuses on logistics, production, operational awareness, and efficiency.

Rather than automating clicks, Skunkworks acts as an intelligent operations manager that keeps your empire running smoothly while respecting the game's mechanics and API.

---

# Current Features

Milestone 1 — Operational Dashboard

Current capabilities include:

- Live API authentication
- Player information
- Fleet operational dashboard
- Runtime Snapshot Manager
- Snapshot Intelligence
- Probe Intelligence
- Sector Intelligence
- Fleet Intelligence
- World Model
- World Builder
- Knowledge Layer
- Gameplay Knowledge
- Crafting Knowledge
- Resource Knowledge
- Movement Knowledge
- Operational Layer

    - Operations Facade
    - Fleet Service
    - Probe Service
    - Travel Service
    - Manufacturing Service
    - Inventory Service
    - Mining Service
    - Galaxy Service
- Planner

    - Rule-based planning
    - Task model
    - Priority system
    - Persisted Desired State
    - Manufacturing, mining, fuel, inventory, and travel rules
- Versioned SQLite Data Engine
- Durable galaxy, probe, resource, visit, and event history
- Interactive and remembered probe selection
- Shared application configuration
- Developer Toolkit

Developer Toolkit (Planned)

- API Explorer
- JSON Explorer
- Snapshot Comparison
- Recipe Explorer
- Manufacturing Explorer

---

# Core Principles

Skunkworks is built around three simple ideas:

- **Awareness** — Always know the current state of your fleet.
- **Desired State** — Define what your fleet should become.
- **Planning** — Automatically determine the most efficient path between the two.

---

# Design Philosophy

## Desired State

Players describe **what** they want.

Skunkworks determines **how** to achieve it.

---

## Planning Over Scripting

Instead of executing fixed sequences of actions, Skunkworks evaluates the current game state and continuously replans as conditions change.

---

## Safety First

The planner prefers safe and predictable behavior over risky optimizations.

Whenever game mechanics introduce tradeoffs, Skunkworks presents recommendations instead of making hidden assumptions.

---

## Transparency

Every action taken by the planner should be understandable.

The player should always know:

- What Skunkworks is doing
- Why it is doing it
- What it plans to do next

---

# Current Architecture

```
Infrastructure
    │
    ▼
GameClient
    │
    ├──────────────┬────────────────┐
    ▼              ▼                ▼
SnapshotManager  RecipeManager   Data Engine
    │              │                │
    ▼              ▼                ▼
Runtime Snapshot  Recipes     History + Goals
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
World Builder
    │
    ▼
World Model
    │
    ├──────────────┐
    ▼              ▼
Dashboard     Operational Layer
                   │
                   ├── FleetService
                   ├── ProbeService
                   ├── TravelService
                   ├── ManufacturingService
                   ├── InventoryService
                   ├── MiningService
                   └── GalaxyService
                   │
                   ▼
               Planner
                   │
                   ▼
            Automation (Future)
```

Each layer has a single responsibility and communicates only with adjacent layers. The Operational Layer combines the live World Model with supporting game knowledge—including live crafting recipes and static gameplay rules—to answer higher-level operational questions without exposing implementation details to the Planner.

This architecture allows Skunkworks to grow without tightly coupling systems together.

---

# Roadmap

## ✅ Milestone 1 — Operational Dashboard

Completed

- Live API connection
- Runtime Snapshot Manager
- Fleet dashboard
- Resource Intelligence
- Developer Toolkit

---

## ✅ Milestone 2 — Operational Intelligence

Completed

- Snapshot Intelligence
- Probe Intelligence
- Sector Intelligence
- Fleet Intelligence
- World Model
- World Builder
- Operational dashboard

---

## ✅ Milestone 3 — Operational Layer

Completed

- Operations facade
- Fleet Service
- Probe Service
- Travel Service
- Manufacturing Service
- Operational manufacturing reasoning
- Manufacturing feasibility analysis
- Missing resource analysis
- Operations facade

Completed

- Planner framework
- Rule architecture
- Task model
- Priority system
- Dashboard integration

---

## ✅ Missions 11–13 — Constraint-Based Planning

Completed

- Persistent Desired State configuration
- Manufacturing goals and feasibility recommendations
- Manufacturing-shortage and resource-reserve mining plans
- Fuel reserve planning
- Inventory capacity planning
- FCC travel routing and blocker analysis
- Durable local galaxy access
- Selected-probe planning context

## ✅ Mission 14 — Safe Execution Foundation

- Typed dry-run commands
- Preflight validation
- Execution policy
- Idempotency and action journal

## ✅ Missions 15–16 — Travel Safety and Routing

- Player-selectable cautious, balanced, bold, and custom safety profiles
- Collision, container, integrity, black-hole, and Manny-loss warnings
- Live damage-rule, improvement, and SCUT-network context
- Direct versus segmented FCC route comparison
- SCUT transit-corridor recognition
- Cumulative route-risk calculations
- Advisory risk acknowledgement without removing player choice

### Automation

- Execute planner decisions
- Fleet logistics
- Production automation

### Desired State

- User-facing objective editor
- Fleet configuration
- Per-probe policy overrides

---

# Project Status

🚧 Active Development

Missions 11–16 complete. Next: Mission 17 — opt-in automation runtime.

0.7.0

Current Milestone

Missions 15–16 — Travel Safety and Routing (Complete)

Current Work

- Persisted production, resource, fuel, inventory, and travel goals
- Manufacturing and mining recommendations
- Fuel and cargo-capacity safeguards
- Deterministic FCC travel routing
- Configurable travel-safety profiles
- Route collision and container-detachment probabilities
- Arrival-integrity estimates
- Black-hole and forgotten-Manny warnings
- SCUT-protected route detection
- Durable galaxy access
- API v104 compatibility and rate-limit awareness
- Authoritative Manny task-state loading
- Interactive and CLI probe selector
- Explicit per-probe operational context
- Complete capability gateways for game controls
- Messaging, missions, storage, logs, alerts, SCUT, and community access
- FCC galaxy and sector-map foundation
- Versioned SQLite Data Engine
- Remembered focused probe
- Probe, sector, resource, visit, message, alert, and mission history

Skunkworks now provides live operational information directly from the Von Neumann Probe API, including:

- Fleet status
- Resource Intelligence
- Runtime snapshots

The intelligence, planning, safety, and pre-automation boundaries are complete.
Development now moves to Mission 17: the opt-in automation runtime that can
approve and dispatch prepared commands.

Current Capabilities:

- Live API connection
- Runtime snapshot management
- World Model
- World Builder
- Gameplay Knowledge
- Crafting Knowledge
- Resource Knowledge
- Movement Knowledge
- Operational Layer
- Fleet Service
- Manufacturing Service
- Probe Service
- Travel Service
- Inventory Service
- Mining Service
- Galaxy Service
- Manufacturing feasibility analysis
- Recursive dependency analysis
- Recursive resource analysis
- Manufacturing reports
- Fleet Intelligence
- Probe Intelligence
- Sector Intelligence
- Snapshot Intelligence
- Operational dashboard
- Live crafting recipes
- RecipeManager
- API compatibility validation
- Canonical v104 telemetry normalization
- Constraint-based Desired State planning
- FCC travel routing
- Typed dry-run command preparation
- Execution policy and preflight validation
- Idempotency fingerprints and action journal
- Advisory travel risk intelligence
- Direct, segmented, and SCUT route comparison

---

# Long-Term Vision

Skunkworks is designed to become more than an automation tool.

Its purpose is to function as an intelligent operations manager capable of:

- Monitoring your fleet
- Maintaining production goals
- Maintaining an accurate, continuously synchronized local model of the discovered universe
- Identifying the operational constraints preventing the player's desired state
- Managing logistics
- Optimizing resource gathering
- Preparing infrastructure before it is needed
- Reducing repetitive gameplay while keeping the player in control

The player defines the destination, Skunkworks determines the route.

Skunkworks combines live operational intelligence from the World Model with static game knowledge from the Knowledge Layer through its Operational Layer. This allows the Planner to identify operational constraints, generate explainable task queues, and continuously adapt recommendations as the game state evolves—all without relying on hardcoded automation.

The Planner transforms that information into an ordered task queue based on the player's goals. Rather than following fixed scripts, Skunkworks continuously evaluates the fleet, reprioritizes work as conditions change, and performs as much of the operational workload as the player chooses to automate.

---

# Acknowledgements

Skunkworks is inspired by the engineering mindset found in the **Bobiverse** novels by **Dennis E. Taylor**.

This project is an independent, open-source companion application for the **Von Neumann Probe** game. It is not affiliated with or endorsed by the game's developer or by the Bobiverse intellectual property.

---

# License

License information will be added before the first public release.
