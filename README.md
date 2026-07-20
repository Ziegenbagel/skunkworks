# Skunkworks

> **Configure your fleet. Define your objectives. Let Skunkworks handle the rest.**

Skunkworks is an autonomous operations manager for the **Von Neumann Probe** game.

Instead of manually managing repetitive tasks, Skunkworks continuously monitors your fleet, compares the current state against your desired state, and intelligently plans the work needed to achieve your objectives.

Its goal is simple:

> **When you sit down to play, your fleet should already be prepared. Skunkworks doesn't replace strategic decision-making—it eliminates repetitive operational work so the player can focus on exploration and long-term planning.**

---

# Mission

Players should focus on exploration, expansion, and strategy.

Skunkworks focuses on logistics, production, and efficiency.

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
- Inventory Intelligence
- Resource Intelligence
- Fleet Intelligence
- World Model
- World Builder
- Knowledge Layer
- Gameplay Knowledge
- Crafting Knowledge
- Resource Knowledge
- Movement Knowledge
- Recursive dependency analysis
- Recursive resource analysis
- Manufacturing reports
- Shared application configuration
- Developer Toolkit

Developer Toolkit includes:

- API Explorer
- JSON Tree Explorer
- Snapshot Comparison Tool
- Gameplay Explorer
- Recipe Viewer
- Dependency Viewer
- Raw Resource Viewer
- Manufacturing Report

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
World Builder
    │
    ▼
World Model
    │
    ▼
Knowledge Layer
    │
    ▼
Reports
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

Each layer has a single responsibility and communicates only with adjacent layers.

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
- Inventory Intelligence
- Resource Intelligence
- Fleet Intelligence
- World Model
- World Builder
- Operational dashboard

---

## 🚧 Milestone 3 — Knowledge Layer

Completed

- gameplay.json integration
- KnowledgeLoader
- GameplayKnowledge
- CraftingKnowledge
- ResourceKnowledge
- MovementKnowledge
- Recursive dependency analysis
- Recursive resource analysis
- Manufacturing Report
- Gameplay Explorer
- Recipe Viewer
- Dependency Viewer
- Raw Resource Viewer

Next

- Planner design
- Manufacturing intelligence
- Recommendation engine

---

## Planned Milestones

### Planner

- Production planning
- Mining recommendations
- Build priorities

### Automation

- Execute planner decisions
- Fleet logistics
- Production automation

### Desired State

- User objectives
- Fleet configuration
- Production goals

---

# Project Status

🚧 Active Development

Current Version

0.6.0

Current Milestone

Planner Design

Skunkworks now provides live operational information directly from the Von Neumann Probe API, including:

- Fleet status
- Resource Intelligence
- Runtime snapshots

Development is currently focused on designing the Planner, which will combine the live World Model with the Knowledge Layer to generate intelligent operational recommendations.

Current Capabilities:

- Live API connection
- Runtime snapshot management
- World Model
- World Builder
- Gameplay Knowledge
- Crafting Knowledge
- Resource Knowledge
- Movement Knowledge
- Recursive dependency analysis
- Recursive resource analysis
- Manufacturing reports
- Fleet Intelligence
- Inventory Intelligence
- Resource Intelligence
- Snapshot Intelligence
- Operational dashboard

---

# Long-Term Vision

Skunkworks is designed to become more than an automation tool.

Its purpose is to function as an intelligent operations manager capable of:

- Monitoring your fleet
- Maintaining production goals
- Managing logistics
- Optimizing resource gathering
- Preparing infrastructure before it is needed
- Reducing repetitive gameplay while keeping the player in control

The player defines the destination.

Skunkworks combines live operational intelligence with static game knowledge to understand not only the current state of the fleet, but also the rules governing the game world. This separation enables the Planner to generate informed recommendations rather than relying on hardcoded automation.

Skunkworks determines the most efficient path to reach it.

---

# Acknowledgements

Skunkworks is inspired by the engineering mindset found in the **Bobiverse** novels by **Dennis E. Taylor**.

This project is an independent, open-source companion application for the **Von Neumann Probe** game. It is not affiliated with or endorsed by the game's developer or by the Bobiverse intellectual property.

---

# License

License information will be added before the first public release.