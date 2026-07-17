# Planner

## Overview

The Planner is the decision-making engine of Skunkworks.

Its responsibility is to evaluate the current game state and recommend or eventually execute the next best actions.

The Planner does not communicate directly with the game API.

Instead, it consumes information produced by the Intelligence Layer.

---

# Current Status

Mission 6

Operational Dashboard

Current progress:

- Live API communication ✅
- Runtime Snapshot Manager ✅
- Resource Intelligence ✅
- Fleet Intelligence (In Progress)

Planner implementation has not yet begun.

Mission 7 Progress

Completed

- Snapshot Intelligence ✅
- Resource Intelligence ✅
- Inventory Intelligence ✅

Next

- Fleet Intelligence
- World Model
- Knowledge Layer

---

# Planner Inputs

The Planner will receive analyzed information from multiple intelligence modules.

Current planned inputs include:

- Fleet Intelligence
- Resource Intelligence
- Inventory Intelligence
- Snapshot State
- Future Research Intelligence

The Planner should never consume raw API responses directly.

---

# Planner Responsibilities

The Planner will eventually answer questions such as:

- Should another Manny be built?
- Which asteroid should be mined next?
- Should a probe relocate?
- Are additional storage containers required?
- Should another SCUT Relay be constructed?
- Is a resource becoming critically low?
- Which task has the highest priority?

---

# Planner Outputs

The Planner may produce:

- Recommendations
- Priority lists
- Warnings
- Forecasts
- Automation tasks (future)

Example:

```
Priority

1. Build Storage Container
2. Build Manny
3. Build SCUT Relay
4. Build Probe
```

---

# Automation

Automation remains intentionally separated from planning.

Relationship:

```
Planner
    │
    ▼
Recommendations
    │
    ▼
Automation
```

The Planner decides *what* should happen.

Automation decides *how* and *when* those actions are executed.

---

# Future Work

Planned Planner capabilities include:

- Resource forecasting
- Production optimization
- Multi-probe coordination
- Autonomous mining recommendations
- Build queue optimization
- Strategic expansion planning