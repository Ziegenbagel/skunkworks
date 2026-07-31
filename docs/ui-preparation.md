# Mission 24 UI Preparation Package

## Starting Point

Missions 1–23 now provide the UI-independent application core. Mission Control
must consume `MissionControlViewModelBuilder` and operational services; widgets
must not read raw API responses, construct routes, calculate safety, or dispatch
game mutations directly.

The initial UI is a simultaneous macOS, Windows, and Linux desktop release and
preserves the planned aerospace
operations-console identity: matte dark surfaces, restrained cyan/blue
structure, sparse amber/red state accents, readable sans-serif body text,
monospace telemetry, and Copperplate Bold only for major titles.

## Information Architecture

The persistent shell contains:

1. Command bar: connection state, focused-probe selector, global refresh,
   automation mode, pending approvals, and emergency stop.
2. Primary navigation: Overview, Fleet, Operations, Navigation, Industry,
   Communications, Timeline, and Settings.
3. Context rail: selected probe/entity, active warnings, next completion, and
   context links.
4. Main workspace: one of four reusable window archetypes.

Window archetypes:

- Data Pad: dense tables, timelines, queues, and editors.
- Inspector: one probe, Manny, container, asteroid, depot, mission, or event.
- Alert Console: warnings, acknowledgements, approvals, failures, and recovery.
- Navigation Console: galaxy/sector maps, routes, SCUT, hazards, missions, and
  infrastructure overlays.

## Screen Inventory

### Overview

- Fleet readiness, focused-probe status, fuel, storage, Manny utilization, and
  current operation.
- Critical findings and approval queue.
- Upcoming events and away/command briefing.
- Resource sustainability and depot collection warnings.

### Fleet

- Persistent probe selector and fleet table.
- Probe Inspector with systems, fuel, cargo, Mannys, roles, and action history.
- Role assignment and tanker delivery planning.

### Operations

- Planned, active, paused, completed, and failed queues.
- Operation template launcher and step Inspector.
- Pause/resume/cancel controls, blockers, assigned assets, and explanations.
- Command preview, approval, separate hazard acknowledgement, and execution
  lifecycle.

### Navigation

- Galaxy map from durable FCC visit/observation history.
- Sector map for objects, asteroids, containers, Mannys, infrastructure, and
  mission targets.
- Toggleable resource, route, SCUT, hazard, discovery, infrastructure, mission,
  and stale-confidence overlays.
- Route comparison and recovery search corridors.

### Industry

- Manufacturing graph, production priorities, inventory, resource reserves,
  miners, containers, depots, transport cycles, and depletion forecasts.
- Distinct tanker/fuel pipeline presentation; deuterium must never appear as
  ordinary container cargo.

### Communications

- Inbox, outbox, missions, alerts, damage warnings, and game logbook.
- Coordinate suggestions from messages require player review.
- Mission abandonment and outgoing messages require explicit confirmation.
- Game logbook remains player-authored. Generated briefings and reports go to
  the separate Skunkworks Archive.

### Timeline and Settings

- Countdown/ETA timeline with confidence, basis, and drift indicators.
- Desired State, production priority, travel/resource safety, refresh policy,
  and automation-policy editors.
- Cautious, balanced, bold, and custom profiles remain advisory; the UI must
  show warnings without disguising risky choices as impossible choices.

## Design Tokens

Define tokens before individual widgets:

- Surfaces: `void`, `panel`, `panel-raised`, `panel-selected`.
- Structure: `line-subtle`, `line-active`, `cyan`, `blue`.
- State: `nominal`, `notice`, `warning`, `critical`, `unknown`, `stale`.
- Typography: `display`, `body`, `technical`, with tabular numerals for data.
- Spacing: 4 px base scale; density presets for compact and comfortable modes.
- Motion: short state transitions only; respect reduced-motion preferences.
- Focus: visible keyboard focus independent of color.

Every state color needs an icon/label companion. Maintain WCAG AA contrast for
text and controls. Provide scalable SVG icons rather than raster UI chrome.

## Presentation Contract

`src/presentation/mission_control.py` currently exposes:

- connection and focused-probe state;
- fleet summary;
- focused-probe fuel, inventory, and Manny summary;
- mining depots;
- operational health and findings;
- unified events;
- durable operations, action history, and Skunkworks archive.

Add screen-specific presenters beside this module. Presenters may format
durations and resource precision, but business decisions remain in operational
services.

## Required Global States

Every screen must render intentionally under:

- connected;
- refreshing;
- stale;
- disconnected;
- limited telemetry / outside SCUT range;
- blind or unknown sector;
- rate limited with retry time;
- automation paused;
- emergency stop active;
- empty/new account;
- partial API failure.

## Mutation Interaction Contract

All mutations follow one interaction pattern:

1. UI requests a typed command or confirmed gateway action.
2. Preview shows target probe, action, reason, cost, blockers, and warnings.
3. Player approves the command and separately acknowledges recommended risk.
4. Runtime refreshes authoritative state and repeats preflight.
5. UI displays lifecycle events and the replanned result.

Emergency stop is persistent, globally visible, keyboard reachable, and never
hidden inside a settings screen.

## Build Sequence

1. Choose a cross-platform desktop UI runtime and establish macOS, Windows,
   and Linux packaging and CI build targets together.
2. Build tokens, typography, SVG icon primitives, and accessibility baseline.
3. Build the shell, probe selector, connection states, and four archetypes.
4. Connect Overview to the read-only presentation model.
5. Build Fleet and Industry Inspectors.
6. Build Operations queues, preview, approval, and emergency stop.
7. Build Navigation Console and overlays.
8. Build Communications, Timeline, Archive, and policy editors.
9. Add responsive behavior, keyboard navigation, reduced motion, and visual
   regression fixtures on all three operating systems.
10. Produce signed/notarized macOS, signed Windows, and packaged Linux release
    candidates from the same versioned source and asset set.
11. Validate every supported routine game action without requiring the game
    website or configuration-file editing.

## Inputs Needed at Mission 24 Kickoff

The remaining product choices are intentionally small:

- Cross-platform UI runtime and packaging strategy.
- Whether Copperplate Bold can be bundled or must use an installed-font
  fallback.
- Preferred initial density: compact operations console or comfortable desktop.
- Any visual references or sketches from the brainstorming work that should be
  treated as binding rather than inspirational.

Everything else—screen scope, state vocabulary, safety interactions, data
boundaries, navigation domains, and visual direction—is ready to implement.

## Cross-Platform Release Gate

Mission 24 is not complete until the same feature set is verified on current
macOS, Windows, and mainstream Linux desktop environments. Platform-specific
differences may affect packaging, signing, fonts, filesystem paths, key
bindings, notification integration, and window chrome, but may not create
different operational capabilities or safety behavior.
