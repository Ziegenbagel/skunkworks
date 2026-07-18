# Planner

## Overview

The Planner is the decision-making engine of Skunkworks.

Its responsibility is to evaluate the current game state and recommend or eventually execute the next best actions.

The Planner does not communicate directly with the game API.

Instead, it consumes information produced by the Intelligence Layer.

---

# Current Status

Mission 7 Complete

Foundation completed:

- Live API communication ✅
- Runtime Snapshot Manager ✅
- Snapshot Intelligence ✅
- Inventory Intelligence ✅
- Resource Intelligence ✅
- Fleet Intelligence ✅
- World Builder ✅
- World Model ✅
- Operational Dashboard ✅

The Planner implementation has not yet begun.

Current focus:

Mission 8 — Knowledge Layer

The next milestone establishes the Planner's static knowledge base by separating game rules from the live operational state.

---

# Planner Inputs

The Planner will receive analyzed information from multiple intelligence modules.

Current planned inputs include:

Live World State

- World Model
- Fleet Intelligence
- Resource Intelligence
- Inventory Intelligence
- Snapshot Intelligence

Static Game Knowledge

- Recipes
- Build costs
- Craft times
- Object definitions
- Manufacturing rules

The Planner should never consume raw API responses directly.

---

# Planner Responsibilities

The Planner will eventually answer questions such as:

- Should another Manny be built?
- Should another storage container be built?
- Should another printer be produced?
- Should manufacturing pause until resources arrive?
- Which asteroid should be mined next?
- Should a probe relocate?
- Should another SCUT Relay be constructed?
- Is a resource becoming critically low?
- Which task has the highest operational priority?

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

- Hub manufacturing planning
- Resource forecasting
- Production optimization
- Multi-probe coordination
- Autonomous mining recommendations
- Build queue optimization
- Strategic expansion planning
- Operational health assessment
- Risk-aware decision making

---

# Planner Philosophy

The Planner combines two sources of information:

1. **World Model** — the current operational state of the game.
2. **Knowledge Layer** — the rules, recipes, and mechanics that govern the game.

By separating live state from static knowledge, the Planner can make informed decisions without depending directly on API responses or configuration files.