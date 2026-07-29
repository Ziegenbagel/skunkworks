# Skunkworks Engineering Rules

This document defines the engineering principles used throughout the Skunkworks project.

These rules exist to keep the project maintainable as it grows.

When a design decision conflicts with these rules, the implementation should be reconsidered before adding complexity.

---

# Core Principles

## 1. Single Responsibility

Every module should have one clearly defined responsibility.

Examples:

- GameClient communicates with the API.
- SnapshotManager stores snapshots.
- RecipeManager manages crafting recipes.
- WorldBuilder constructs the World Model.
- Dashboard displays information.

Avoid classes that both retrieve data and reason about it.

---

## 2. Layered Architecture

Information flows downward through the application.

```
Game API
    ↓
Infrastructure
    ↓
Intelligence
    ↓
World Model
    ↓
Operational Layer
    ↓
Planner
    ↓
Automation
```

Lower layers should never depend on higher layers.

---

## 3. Explainable Planning

Every planner recommendation should be explainable.

The planner should always be able to answer:

- What should happen?
- Why should it happen?
- Which operational constraints caused the recommendation?

Recommendations should never appear as "magic."

---

## 4. Normalize Only When Valuable

Raw API responses should remain unchanged unless normalization provides meaningful value.

Examples:

Good normalization:

- Recipe lookup by ID
- Fuel percentage
- Inventory percentage
- Unified resource models

Poor normalization:

- Renaming fields without benefit
- Copying API data unnecessarily

---

## 5. Prefer Live Data

When the API provides authoritative information, Skunkworks should use it directly.

Avoid maintaining duplicate local databases.

Examples:

- Crafting recipes come from `/api/crafting-recipes`
- Runtime state comes from snapshots

Static files should only be used when no API source exists.

---

## 6. Keep Knowledge Separate from State

Static knowledge and live game state solve different problems.

Examples of knowledge:

- Gameplay rules
- Crafting recipes
- Resource definitions

Examples of state:

- Current probe inventory
- Fuel
- Fleet status
- Sector resources

They should not be mixed together.

---

## 7. Services Answer Questions

Operational services should answer questions rather than execute workflows.

Good examples:

```

probe.is_idle()
travel.travel_ready()
manufacturing.can_build("manny")

```

Poor examples:

```

manufacture_everything()
prepare_for_expansion()

```

The Planner combines answers into decisions.

---

## 8. Planner Owns Decisions

Services provide facts.

The Planner makes decisions.

Avoid embedding planning logic inside operational services.

---

## 9. World Model is the Source of Truth

Once constructed, application state should come from the World Model.

Most systems should not continue requesting raw API data.

---

## 10. Infrastructure Should Not Think

Infrastructure retrieves and stores data.

It should not perform business logic.

Examples:

GameClient:

- Requests API endpoints.

SnapshotManager:

- Saves snapshots.

RecipeManager:

- Organizes recipes.

Reasoning belongs elsewhere.

---

## 11. Prefer Composition Over Coupling

Components should communicate through well-defined interfaces.

Avoid exposing internal implementation details between layers.

---

## 12. Build Small Vertical Slices

Complete one working feature before beginning the next.

Each milestone should produce:

- Working code
- Updated documentation
- A clean commit

Avoid partially implemented systems.

---

## 13. Temporary Code Must Be Temporary

Debug prints, experimental code, and verification helpers should be removed immediately after successful testing.

Production code should remain clean.

---

## 14. Documentation Evolves With Code

Major architectural changes should update:

- README
- Architecture documentation
- API Notes
- Rules (when applicable)

Documentation is part of the project, not an afterthought.

---

# Coding Style

- Prefer readable code over clever code.
- Favor explicit names over abbreviations.
- Keep functions focused.
- Keep files focused.
- Avoid unnecessary abstraction.
- Add comments only when intent is not obvious.

---

# Long-Term Goal

Skunkworks is intended to become an explainable autonomous operations manager.

The player defines objectives.

Operational services describe the current situation.

The Planner determines the work required.

Automation performs approved actions.

Every layer should remain independently understandable, testable, and replaceable.