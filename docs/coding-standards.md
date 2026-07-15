# Skunkworks Coding Standards

Version: 0.1.0

---

## Project Philosophy

Skunkworks is built in layers.

Research
↓
Developer Toolkit
↓
Application
↓
Automation

Automation should never rely on assumptions.
Every feature should be built upon verified observations of the game API.

---

## Development Philosophy

- Build small.
- Test often.
- Keep every version working.
- Prefer reusable tools over one-off scripts.
- Organize first, optimize later.

---

## Folder Organization

src/
Application source code.

tools/
Developer Toolkit.

data/
Snapshots and research data.

docs/
Project documentation.

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

Every tool should display:

Skunkworks Laboratory

Tool Name

Version

Purpose

before performing work.

---

## Application Standard

The main application should identify itself as:

Skunkworks

Mission Control

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

Developer Tool

↓

Verified Understanding

↓

Application Feature

↓

Automation

Never skip steps.

---

## Commit Messages

Commit messages should describe completed work.

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