# Skunkworks Coding Standards

Version: 0.2.0

---

## Project Philosophy

Skunkworks is built in layers.

Research
↓
Developer Toolkit
↓
Knowledge / API Research
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

Every feature should be built upon verified observations of the game API.

---

## Development Philosophy

- Build small.
- Test often.
- Keep every version working.
- Prefer reusable tools over one-off scripts.
- Organize first, optimize later.
- One responsibility per component.
- Prefer composition over large classes.
- Complete one working feature at a time.
- Remove temporary verification code immediately after testing.
- Update documentation before committing.

---

## Folder Organization

src/
Application source code.

tools/
Developer Toolkit.

data/
Runtime snapshots and cached research data.

docs/
Project documentation.

tests/
Automated tests.

.github/
Repository automation.

---

## Naming

Python modules:
snake_case.py

Classes:
PascalCase

Functions:
snake_case()

Constants:
UPPER_CASE

---

## Developer Toolkit Standard

Every tool should define:

APP_NAME

APP_VERSION

DIVIDER

Developer tools should present a consistent identity including:

Skunkworks Laboratory

Tool Name

Version

Purpose

before performing work.

---

## Application Standard

The main application should identify itself as:

Skunkworks

Skunkworks

Version

The player application and Developer Toolkit should have distinct identities.

---

## Versioning

Developer tools maintain independent version numbers.

Example:

JSON Tree Explorer 0.1.0

API Explorer 0.1.0

Snapshot Comparator 0.1.0

Application versioning is independent.

---

## Development Workflow

Research
↓
Developer Toolkit
↓
Verified Understanding
↓
Knowledge Layer
↓
Operational Layer
↓
Planner
↓
Automation

Never skip steps.

---

## Commit Messages

Commit messages should describe completed work. Commit only completed, working features.

Examples:

Build Mission Control dashboard

Add JSON Tree Explorer

Document API endpoint

Implement resource planner

Avoid vague commit messages.

---

## Core Principle

Whenever the game hides operational information that the API provides,
Skunkworks should make that information understandable and actionable.

Skunkworks should assist the player,
never bypass the game's intended mechanics.

---

## Mission Completion Workflow

Plan
↓
Implement
↓
Run
↓
Verify
↓
Remove temporary verification code
↓
Update Documentation
↓
Commit
↓
Push

## Service Design

Services should answer questions.

Services should not print output.

Services should not interact with the user interface.

Services should consume normalized application state rather than raw API responses.

Services should expose stable, high-level operations without revealing implementation details.

Services should expose questions, not workflows.

Examples:

    Good:

    probe.is_idle()
    travel.travel_ready()
    manufacturing.can_build("manny")

    Avoid:

    prepare_everything()
    expand_empire()

## Documentation Workflow

After each completed mission:

- Update README
- Update Architecture documentation
- Update Development Log
- Review all documentation for architectural accuracy
- Commit

## Code Review Checklist

Before committing:

✓ Code runs without errors.
✓ Temporary debug code removed.
✓ Naming follows project standards.
✓ Documentation updated.
✓ No duplicated logic introduced.
✓ Architecture still follows layer boundaries.