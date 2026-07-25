# Planner

## Overview

The Planner is the decision-making engine of Skunkworks.

Its responsibility is to evaluate the current game state and recommend or eventually execute the next best actions.

The Planner does not communicate directly with the game API.

Instead, it consumes information produced by the Operational Layer.

The Operational Layer combines the live World Model with the static Knowledge Layer, allowing the Planner to focus on high-level decision making rather than low-level operational reasoning.

---

# Current Status

Mission 10 — Planner Expansion

Completed Foundations

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
- CraftingKnowledge ✅
- ResourceKnowledge ✅
- MovementKnowledge ✅
- Recursive dependency analysis ✅
- Recursive raw resource analysis ✅
- Manufacturing Report ✅

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
- Initial planning engine
- Dashboard integration
- Idle probe assessment

Mission 10

Current Focus

- Task prioritization
- Manufacturing recommendations
- Travel recommendations
- Resource shortage analysis
- Multi-probe planning
- Desired State evaluation

---

# Planner Inputs

The Planner receives operational capabilities rather than raw application state.

Operational Layer

- FleetService
- ManufacturingService
- TravelService
- ProbeService

Future

- GalaxyService
- MessagingService

Supporting Layers

Operational Services consume:

- Fleet
- Probe
- Sector
- Snapshot

Operational Services internally consume:

- World Model
- Knowledge Layer

The Planner should never consume raw API responses, snapshots, or configuration data directly.

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

Example:

```
Task Queue

1. Build 2 Mannys
   Reason:
   Increase mining throughput before expanding storage.

2. Build 5 Storage Containers
   Reason:
   Prepare for additional mining capacity.

3. Manufacture Probe Components
   Reason:
   Prepare next probe for manual assembly.
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

- Planner rule engine
- Event-driven planning
- Prediction-aware planning
- Desired State evaluation
- Manufacturing planning
- Travel planning
- Safety evaluation
- Resource forecasting
- Production optimization
- Multi-probe coordination
- Autonomous mining recommendations
- Logistics planning
- Build queue optimization
- Strategic expansion planning
- Operational health assessment
- Risk-aware decision making
- Task optimization
- Task scheduling
- Goal prioritization
- Explainable planning
- Goal-based planning

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

# Planner Principles

The Planner is goal-driven.

Players define the desired outcome.

The Planner determines the most efficient sequence of work required to reach that outcome.

The Planner may temporarily reorder work if doing so results in a faster or more efficient path toward the player's objectives.

Every generated task should explain why it exists so the player can understand the Planner's reasoning.

The Planner continuously reevaluates the current operational state rather than following fixed scripts, allowing recommendations to adapt as conditions change.