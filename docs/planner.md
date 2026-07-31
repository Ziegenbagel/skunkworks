# Planner

## Overview

The Planner is the decision-making engine of Skunkworks.

Its responsibility is to evaluate the current game state and recommend or eventually execute the next best actions.

The Planner does not communicate directly with the game API.

Instead, it consumes information produced by the Operational Layer.

The Operational Layer combines the live World Model with the static Knowledge Layer, allowing the Planner to focus on high-level decision making rather than low-level operational reasoning.

---

# Current Status

Missions 11–13 — Constraint-Based Planner

Status:
Complete

Mission 14 — Safe Execution Foundation ✅

- Typed command model
- Planner-to-command translation
- Preflight validation
- Observe, approve, and automatic policy model
- Automatic-mode command allowlist
- Per-cycle command limits
- Stable idempotency fingerprints
- Durable action journal
- Dashboard dry-run preview
- No mutation dispatcher

Next Mission

Mission 15 — Opt-In Automation Runtime

Mission 7

- Live API communication ✅
- Runtime Snapshot Manager ✅
- Snapshot Intelligence ✅
- Probe Intelligence ✅
- Sector Intelligence ✅
- Fleet Intelligence ✅
- World Builder ✅
- World Model ✅
- Operational Dashboard ✅

Mission 8

- KnowledgeLoader ✅
- GameplayKnowledge ✅
- ResourceKnowledge ✅
- MovementKnowledge ✅
- Live RecipeManager ✅
- API-backed recipe database ✅

Mission 9 — Operational Layer ✅

- Operations facade ✅
- FleetService ✅
- ManufacturingService ✅
- TravelService ✅
- ProbeService ✅
- Initial Planner framework ✅
- Task model ✅
- Dashboard integration ✅

The Planner foundation is now implemented.

Current capabilities include:

- Structured Task model
- Declarative Desired State model
- Typed production, resource, fuel, inventory, and travel goals
- JSON defaults with SQLite-persisted overrides
- Structured task constraints
- Rule-based planning architecture
- Independent planning rules
- Shared priority system
- Dashboard integration
- Safety planning
- Manufacturing planning
- Mining and reserve planning
- Fuel planning
- Inventory-capacity planning
- FCC travel routing
- Durable galaxy-map access
- Idle probe assessment

Mission 11 — Manufacturing Intelligence ✅

- Production goals become craft or preparation tasks.
- Recursive recipe shortages become mining requirements.
- Fabricator, inventory, fuel, and probe-state blockers remain explicit.

Mission 12 — Mining and Resource Intelligence ✅

- Desired resource reserves generate shortage tasks.
- Current-sector targets are ranked by amount and composition.
- Idle Manny and selected-probe availability are enforced.
- Fuel reserves generate deuterium recovery recommendations.

Mission 13 — Logistics and Navigation Intelligence ✅

- Minimum free-capacity goals generate cargo tasks.
- Desired destinations generate shortest FCC routes.
- Travel tasks expose fuel, state, and telemetry blockers.
- Historical galaxy data is available through GalaxyService.

Mission 10.5 — Fleet Interface

- Replace --probe-id.
- Interactive probe selector.
- Remember focused probe.
- Fleet overview screen.
- Foundation for multi-probe dashboard.

---

# Planner Inputs

The Planner receives operational capabilities rather than raw application state.

Operational Layer

ManufacturingService
        │
        ▼
RecipeManager

- FleetService
- ManufacturingService
- TravelService
- ProbeService

- InventoryService
- MiningService
- GalaxyService

Future

- MessagingService policy and automation

Supporting Layers

Operational Services consume:

- Fleet
- Probe
- Sector
- Snapshot
- Authoritative Manny state
- Selected Probe Context
- Galaxy Map

Operational Services internally consume:

- World Model
- Knowledge Layer

The Planner should never consume raw API responses, snapshots, or configuration data directly. The Planner should ask Operational Services questions rather than inspecting the World Model directly whenever an operational capability exists.

---

# Planner Responsibilities

Manufacturing

- Should another Manny be built?
- Should another storage container be built?
- Should another printer be produced?
- Should manufacturing pause until resources arrive?
- What raw resources are required to complete a build?
- Which manufacturing dependencies are missing?
- Is a production chain currently achievable?
- Which resources are preventing production?

Logistics

- Which asteroid should be mined next?
- Should a probe relocate?
- Should another SCUT Relay be constructed?

Operational Health

- Is a resource becoming critically low?
- Which task has the highest operational priority?

Probe Management

- Is the current probe idle?
- Should manufacturing begin?
- Should mining begin?
- Should travel begin?
- Is fuel sufficient?
- Is inventory capacity becoming limited?

Constraint Analysis

- What prevents the Desired State?
- What dependency is blocking progress?
- Which blocker should be removed first?
- Which recommendation unlocks the most future work?

---

# Planner Outputs

The Planner produces an ordered task queue.

Each task describes:

- Category
- Action
- Target
- Quantity
- Priority
- Reason
- Constraint

Example:

```
Action:
Build Manny

Reason:
Increase mining throughput.

Constraint:
Missing 2.6 Metal.
```

Future examples may also include:
Manufacturing Assessment

Cannot build Manny

Missing:
-Metals: 2.58
-Organic Compounds: 0.90
-Deuterium: 0.86

---

# Automation

Automation remains intentionally separated from planning.

Relationship:

```
Planner
    │
    ▼
Task Queue
    │
    ▼
Automation
```

The Planner decides *what* should happen.

Automation decides *how* and *when* those actions are executed.

---

# Future Work

Planned Planner capabilities include:

Planning Engine

- Event-driven planning
- Prediction-aware planning

Operational Intelligence

- Constraint solver
- Prediction engine
- Resource forecasting
- Logistics planning
- Cross-probe planning
- Message-driven coordination

Optimization

- Goal prioritization
- Task optimization
- Task scheduling
- Production optimization
- Strategic expansion planning

Fleet Intelligence

- Multi-probe coordination
- Autonomous mining recommendations
- Build queue optimization

Desired State

- User-facing goal editor
- Per-probe policy overrides
- Goal conflict resolution

---

# Planner Philosophy

The Planner consumes the Operational Layer rather than interacting directly with lower-level application models.

The Planner reasons about operational domains such as Fleet, Probe, and Sector rather than raw API responses or user interface concepts. This allows planning logic to remain stable even as the underlying implementation evolves.

Operational Services combine two sources of information:

1. **World Model** — the current operational state of the game.
2. **Knowledge Layer** — the rules, recipes, and mechanics that govern the game.

By separating operational reasoning into dedicated services, the Planner remains focused on answering higher-level questions such as:

- What should happen next?
- Which recommendation has the highest priority?
- Which objective most effectively advances the player's Desired State?

This separation allows the World Model, Knowledge Layer, and Operational Layer to evolve independently while presenting the Planner with a stable, task-oriented interface.

Rather than generating scripted actions, the Planner identifies the operational constraints preventing the player's Desired State. By resolving the highest-impact constraints first, Skunkworks continuously adapts its recommendations as the game state evolves.

# Planning Pipeline

Desired State
        │
        ▼
Current Operational State
        │
        ▼
Gap Analysis
        │
        ▼
Constraint Analysis
        │
        ▼
Task Generation
        │
        ▼
Task Prioritization
        │
        ▼
Automation (optional)

# Planner Principles

The Planner is goal-driven.

Players define the desired outcome.

The Planner determines the most efficient sequence of work required to reach that outcome.

The Planner may temporarily reorder work if doing so results in a faster or more efficient path toward the player's objectives.

Every generated task should explain why it exists so the player can understand the Planner's reasoning.

The Planner continuously reevaluates the current operational state rather than following fixed scripts, allowing recommendations to adapt as conditions change.

The Planner prefers operational queries over direct inspection of application state, allowing implementation details to evolve without affecting planning logic.

The Planner should ask questions before making decisions.
