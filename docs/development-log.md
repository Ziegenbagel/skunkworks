# Development Log

---

## 2026-07-13

### Sprint 1 — Mission Control

Completed:
- Finalized project directory structure.
- Added project documentation.
- Built the first Dashboard UI.
- Connected the dashboard to live API data.
- Refactored main.py into an application coordinator.
- Established API → UI architecture.

Current Status:
- API communication working.
- Dashboard operational.
- Live player information displayed.

Next Session:
- Populate Fleet section with live probe data.
- Create Probe model.
- Begin Current State engine.

## 2026-07-14

# Session: API Exploration & Developer Toolkit

## Accomplishments

### Mission Control
- Refactored the application to retrieve the player's probe list dynamically.
- Added support for selecting a probe by ID using `--probe-id`.
- Sector snapshots are now automatically saved for the selected probe.

### API Client
- Added `/api/probes` support.
- Updated sector requests to use `/api/probe/{probeId}/sector` instead of relying on the currently selected probe.

### Developer Toolkit

#### JSON Tree Explorer
- Improved output formatting.
- Added object type summaries for lists.
- Added representative structure output.
- Improved readability for nested collections.

#### Snapshot Compare
- Created Version 0.1.0.
- Compares semantic object counts rather than raw JSON.
- Confirms structural differences between snapshots.

## Major Discoveries

- Probe-specific sector snapshots are now supported.
- Sector snapshots appear to represent observable physical objects rather than complete operational state.
- Inventory correctly reflects onboard assets.
- Deployed Mannys do not appear to be represented as inventory items.
- Detached containers appear as sector objects.

## Next Research Goals

- Identify the endpoint responsible for active Manny operations.
- Identify endpoints for probe task state.
- Continue mapping the API before implementing automation.

## 2026-07-15

Version 0.5.0
--------------

Major Features
• Added SnapshotManager service.
• Added runtime snapshot storage.
• Added ResourceAnalyzer intelligence layer.
• Added live Fleet dashboard.
• Added live Resource Intelligence dashboard.
• Introduced shared application configuration (config.py).

Developer Tools
• JSON Tree Explorer
• Snapshot Comparison Tool
• API Explorer

Architecture
• Dashboard now consumes analyzed data rather than raw API responses.
• SnapshotManager is the single source for runtime snapshots.

Verified API Discoveries
• /api/probes provides live probe status.
• Mineable resources are exposed through
  sector.objects -> solar_system -> minableTargets.
• resourceAmounts contains remaining resources.
• resourceComposition contains resource percentages.

## 2026-07-16

## Mission 7 - Operational Intelligence

Completed:

- Added Snapshot Intelligence
- Added Inventory Intelligence
- Refactored Resource Intelligence
- Added support for persistent and dynamic mineable objects
- Added Object Inspector developer tool
- Improved dashboard organization

Major Discoveries:

- Mineable resources come from two API representations:
  - `solar_system.minableTargets`
  - `sector.objects` where `mannyMineable == true`
- Dynamic mineable objects can represent wandering resource opportunities.
- Resource Intelligence now normalizes both representations into a single internal model.

## 2026-07-17

## Mission 7 - World Intelligence Architecture

Completed:

- Introduced WorldModel as the application's unified state representation.
- Added WorldBuilder to assemble the WorldModel from Intelligence modules.
- Added FleetAnalyzer.
- Added operational fleet metrics (Available / Busy).
- Refactored the Dashboard to consume the WorldModel exclusively.
- Improved Fleet dashboard with Operational, Status Summary, and Probe Details sections.
- Renamed dashboard sections to distinguish Probe Inventory from Sector Resources.

Architecture Improvements:

- Established a five-layer architecture:
  - Infrastructure
  - Intelligence
  - Construction
  - Domain
  - Presentation
- Removed analyzer orchestration from `main.py`.
- Centralized application state construction within WorldBuilder.
- Standardized the analyzer → WorldBuilder → WorldModel workflow.

Project Milestone:

Mission 7 is now complete.

Skunkworks has evolved from an API monitoring tool into a layered application capable of building a normalized operational model of the game world.

Next Mission:

Mission 8 — Knowledge Layer

Goals:

- Load gameplay.json
- Separate static game knowledge from live game state.
- Build reusable knowledge services.
- Prepare manufacturing intelligence.
- Provide the Planner with game rules, recipes, and object definitions.

## 2026-07-18

## Mission 8 - Knowledge Layer

Completed:

- Added KnowledgeLoader.
- Integrated `gameplay.json` into the project.
- Added GameplayKnowledge.
- Added CraftingKnowledge.
- Added ResourceKnowledge.
- Added MovementKnowledge.
- Implemented normalized recipe access.
- Implemented recursive dependency analysis.
- Implemented recursive raw resource analysis.
- Added Manufacturing Report.
- Added shared text formatting utilities.
- Added shared time formatting utilities.

Major Discoveries:

- `gameplay.json` serves as the game's rulebook rather than simple configuration.
- Crafting recipes form a dependency graph rather than an isolated list of recipes.
- Raw resources consistently use `*Cost` fields.
- Manufactured components consistently use `*Count` fields.
- Recipe normalization separates raw resources, crafted components, and gameplay effects into a stable internal representation.
- Total manufacturing costs can be derived recursively from normalized recipe data.
- Probe construction is not defined within the crafting system and will require additional API research.

Architecture Improvements:

- Introduced the Knowledge Layer as a distinct architectural layer alongside the World Model.
- Separated static game knowledge from live operational state.
- Established Knowledge Services as the public interface for accessing game rules.
- Added recursive reasoning capabilities built on top of normalized knowledge.
- Introduced Manufacturing Reports as the first assembled knowledge product.

Developer Toolkit:

Added:

- Gameplay Explorer
- Recipe Viewer
- Dependency Viewer
- Raw Resource Viewer
- Manufacturing Report

Project Milestone:

Mission 8 is now complete.

Skunkworks now separates:

- Live operational state (World Model)
- Static game rules (Knowledge Layer)

The Knowledge Layer is now capable of deriving manufacturing relationships, dependency trees, and total raw resource requirements directly from the game's rule set.

This establishes the foundation required for production planning, manufacturing intelligence, and the future Planner.

Next Mission:

Mission 9 — Operational Layer

Goals:

- Define Desired State.
- Design Planner inputs and outputs.
- Establish recommendation priorities.
- Design manufacturing planning workflows.
- Integrate the World Model with the Knowledge Layer.

Retrospective (2026-07-28)

The original CraftingKnowledge implementation based on `gameplay.json`
was later replaced by live recipe retrieval from the
`/api/crafting-recipes` endpoint.

Gameplay knowledge remains static, while crafting recipes are now
treated as live game data managed by RecipeManager.

## 2026-07-19

## Mission 8.5 - Knowledge Layer Refinement

Completed:

- Reviewed the public Knowledge Layer API.
- Added `get_raw_resources()` to `CraftingKnowledge`.
- Refactored `ResourceKnowledge` into a consistent knowledge service.
- Standardized Knowledge Layer interfaces across all services.
- Updated developer tools to consume `ResourceKnowledge`.
- Added placeholder documentation for `MovementKnowledge`.

Architecture Improvements:

- Established consistent service-oriented APIs throughout the Knowledge Layer.
- Distinguished Knowledge Services from Knowledge Products.
- Confirmed `KnowledgeLoader` as the sole component responsible for loading static game data.
- Verified that `GameplayKnowledge` remains the public entry point for `gameplay.json`.
- Confirmed developer tools consume Knowledge services rather than raw game data.

Repository Review:

- Verified no direct access to `gameplay.json` exists outside the Knowledge Layer.
- Verified Knowledge loading is centralized through `KnowledgeLoader`.
- Verified developer tools remain presentation-only and do not contain business logic.
- Confirmed the Knowledge Layer provides a stable foundation for future Operational services.

Project Milestone:

Mission 8.5 is complete.

The Knowledge Layer now exposes a consistent set of reusable services that separate static game knowledge from higher-level reasoning.

Skunkworks is now ready to begin Mission 9 — Operational Layer.

Next Mission:

Mission 9 — Operational Layer

Goals:

- Introduce operational service architecture.
- Build Fleet, Travel, Manufacturing, and Messaging services.
- Separate operational reasoning from game knowledge.
- Prepare the Planner to reason about possible actions rather than raw game data.

## 2026-07-20

## Mission 9 - Operational Layer (Part 1)

Completed:

- Introduced the Operational Layer.
- Added the Operations facade.
- Added FleetService.
- Added ManufacturingService.
- Integrated the Operational Layer into the application startup.
- Added manufacturing feasibility analysis.
- Added missing resource analysis.
- Added Fleet Summary developer tool.

Architecture Improvements:

- Established the Operational Layer as the bridge between the World Model and the future Planner.
- Separated operational reasoning from both the Intelligence Layer and the Knowledge Layer.
- Confirmed operational services consume normalized application state rather than raw API responses.
- Established Operations as the public entry point for higher-level operational capabilities.

Major Discoveries:

- Operational reasoning naturally combines live world state with static game knowledge.
- Manufacturing feasibility can be determined without exposing inventory or recipe implementation details to the caller.
- The Planner can consume Operational Services without depending directly on the World Model or Knowledge Layer.

Project Milestone:

Mission 9 is approximately halfway complete.

Skunkworks has transitioned from collecting and organizing information to performing operational reasoning.

The Operational Layer now answers higher-level questions such as whether an item can be manufactured and which resources are still required.

Next Session:

Mission 9 — Operational Layer (Part 2)

Goals:

- Add TravelService.
- Add GalaxyService.
- Add ProbeService.
- Add MessagingService.
- Add fuel awareness to the operational dashboard.
- Continue preparing the Planner to consume Operational Services.

## 2026-07-21

## Mission 9 - Operational Layer (Part 2)

Completed:

- Added TravelService.
- Added ProbeService.
- Added fuel awareness to the operational dashboard.
- Expanded the Operational Layer with additional probe-centric services.
- Verified Operational Services integrate cleanly with the World Model.

Architecture Improvements:

- Established ProbeService as the centralized interface for probe-specific operational information.
- Separated probe state queries from FleetService to keep service responsibilities focused.
- Continued reinforcing the Operational Layer as the sole interface between the World Model and future planning systems.

Major Discoveries:

- Probe inventory, fuel, and idle state naturally belong together as probe-level operational data.
- Smaller, specialized services scale better than expanding existing services with unrelated responsibilities.
- Operational Services continue to demonstrate that higher-level reasoning can be built without exposing raw application state.

Project Milestone:

Mission 9 is now complete.

The Operational Layer now provides focused services for fleet management, manufacturing, travel, and probe operations. This completes the operational foundation required before introducing the Planner.

Next Mission:

Mission 10 — Planner Framework

Goals:

- Create the Planner framework.
- Introduce the Task model.
- Generate structured tasks instead of direct actions.
- Integrate Planner output into the dashboard.
- Begin production planning.

## 2026-07-24
## Mission 10 - Planner (Part 1)

Completed:
- Introduced the initial Planner framework.
- Added the Task model.
- Integrated Planner output into the Dashboard.
- Implemented the first planning rule for idle probes.
- Established the Planner as a producer of recommendations rather than direct actions.

Major Architecture Refactor:
- Introduced ProbeAnalyzer.
- Introduced SectorAnalyzer.
- Refactored WorldBuilder around Probe and Sector domains.
- Refactored WorldModel to represent Player, Fleet, Probe, Sector, and Snapshot.
- Updated the Dashboard to consume Probe and Sector models directly.
- Retired InventoryAnalyzer.
- Retired FuelAnalyzer.
- Preserved API structures where normalization was unnecessary.

Major Discoveries:
- /api/probe/{probeId} is the authoritative source of probe state.
- Probe state naturally includes inventory, fuel, systems, movement, and navigation.
- /api/probe/{probeId}/sector represents only the observable environment around a probe.
- Sector data becomes unavailable while a probe is traveling at relativistic speed.
- Separating Probe and Sector state more accurately reflects the game's operational model.

Architecture Improvements:
- Shifted the application from UI-oriented models to game-domain models.
- Established Probe and Sector as the primary operational domains.
- Aligned the World Model more closely with the game's API.
- Simplified future expansion by organizing state around real game entities instead of presentation concepts.

Project Milestone:

Mission 10 has begun.

Although Planner development started successfully, implementation paused after the initial planning rule to perform a major architectural refactor. This refactor established a stronger foundation for future planning, prediction, and automation by restructuring the application around the game's native domain model.

Next Session:

Mission 10 — Planner Expansion

Goals:
- Expand planning rules and task generation.
- Introduce task prioritization.
- Add manufacturing recommendations.
- Add travel recommendations.
- Add resource shortage analysis.
- Prepare the Planner for Desired State evaluation.

## 2026-07-28

## Mission 10 - Planner (Part 2)

Completed:

- Introduced rule-based Planner architecture.
- Created Planner rule modules.
- Added Planner priority system.
- Refactored idle planning into an independent rule.
- Added the initial Safety planning rule.
- Introduced shared planner priorities.
- Improved Planner presentation in the Dashboard.
- Updated project architecture documentation.

Architecture Improvements:

- Refactored the Planner into a lightweight coordinator.
- Established independent planning rules with a common interface.
- Separated planning orchestration from planning logic.
- Standardized Task priorities across the application.
- Reinforced the Operational Layer as the Planner's primary interface.

Major Discoveries:

- Planning logic scales more naturally when organized into independent rule modules.
- Operational Services should answer questions on behalf of the Planner rather than exposing internal application state.
- The Planner is evolving toward identifying operational constraints instead of executing scripted behaviors.

Project Milestone:

Mission 10 is approaching completion.

The Planner now has a stable architectural foundation capable of supporting progressively more sophisticated reasoning without requiring future structural refactoring.

Next Session:

Mission 11 — Manufacturing Intelligence

Goals:

- Expand the Safety planning rule.
- Introduce Fuel planning.
- Begin Inventory planning.
- Move additional operational reasoning into Operational Services.
- Continue replacing direct World Model inspection with operational queries.
- Begin implementing constraint-based planning.

## 2026-07-28

## Mission 10 - Recipe Foundation

Completed:

- Added `/api/crafting-recipes` support to GameClient.
- Introduced RecipeManager.
- Replaced the temporary local recipe database with live API-backed recipes.
- Normalized recipes into fast ID-based lookups.
- Verified live loading of all available crafting recipes.

Architecture Improvements:

- Established the game API as the authoritative source for crafting recipes.
- Separated recipe management from manufacturing reasoning.
- Reinforced the principle of preferring live API data over duplicated local data.
- Added RecipeManager as a dedicated infrastructure component.

Major Discoveries:

- The crafting API provides stable recipe identifiers.
- Recipes include manufacturing capability (`craftableBy`), dependency information (`ingredients`), crafting duration, and output metadata.
- The API exposes a richer crafting model than the original `gameplay.json`.

Project Milestone:

Mission 10 is now complete.

The Planner now has both an operational reasoning layer and a live recipe database, providing the foundation for manufacturing planning and future constraint-based reasoning.

Next Session:

Mission 11 — Manufacturing Intelligence

Goals:

- Integrate RecipeManager into ManufacturingService.
- Implement `can_build()`.
- Add missing ingredient analysis.
- Begin dependency-tree planning.

## 2026-07-30

## Mission 11 - Manufacturing Intelligence (Part 1)

Completed:

- Integrated the live RecipeManager with ManufacturingService.
- Replaced obsolete static crafting reports in operational reasoning.
- Corrected manufacturing inventory access to use the selected probe model.
- Implemented live `can_build()` feasibility analysis.
- Added direct missing resource and crafted-item ingredient analysis.
- Added recursive recipe dependency trees.
- Added recursive raw-resource requirement analysis.
- Added focused manufacturing tests.

Architecture Improvements:

- RecipeManager remains an infrastructure lookup component.
- Manufacturing reasoning now lives entirely in ManufacturingService.
- The Planner can consume live manufacturing facts without inspecting recipes
  or probe inventory directly.

Mission 11 has begun.

Part 2:

- Initially modeled missing dependencies as separate production steps.

Upstream Contract Review:

- Reviewed Von Neumann Game API v104 and upstream game services.
- Corrected the production model: the game recursively synthesizes missing
  components inside one final-output craft order.
- Added API compatibility validation and rate-limit awareness.
- Added authoritative Manny state to the World Model.
- Added safe normalization for out-of-range probes and current probe models.
- Corrected canonical resource, movement, and travel rules.
- Added fabricator, probe-state, fuel, and cargo-capacity constraints.
- Synchronized static knowledge with upstream commit
  `e5a5f17342ec5436f1879cd16df2e9906a33e66f`.
- Expanded contract, normalization, travel, and manufacturing tests.

Next Session:

- Define Desired State production goals.
- Introduce the first Manufacturing planner rule using real API actions.

## 2026-07-30

## Capability and Multi-Probe Foundation

Completed:

- Added interactive, ID-based, name-based, and default probe selection.
- Made every probe-scoped capability require an explicit probe ID.
- Added limited telemetry support for owned probes outside SCUT range.
- Added domain gateways for account, probes, storage, Mannies, messaging,
  galaxy observations, missions, and community features.
- Exposed every public Manny task and atomic batch assignment.
- Added logbook, alert, warning, improvement, SCUT, inventory, and movement
  controls.
- Added FCC sector coordinates, neighbors, distance, exploration history, and
  observation-ready galaxy map models.
- Added an application context seam for future UI, Planner, and Automation.

Architecture:

- Gateways own public route construction.
- Intelligence owns map construction and telemetry normalization.
- Operational Services answer questions from normalized state.
- Planner rules decide which real API action should be recommended.
- Automation remains a separate, policy-controlled execution layer.

## 2026-07-30

## Data Engine and Remembered Probe

Completed:

- Added a versioned local SQLite Data Engine.
- Persisted the focused probe and restored it on later launches.
- Added probe-state, sector-observation, and resource history.
- Added fleet-wide and per-probe visited-sector history.
- Added generic durable records for messages, alerts, warnings, missions, and
  future event domains.
- Added best-effort startup history synchronization.
- Added galaxy-map reconstruction from durable history.
- Normalized moving-probe sector responses that omit observable objects.

Live Verification:

- Selected and remembered probe `762`.
- A later argument-free launch restored probe `762`.
- History synchronization stored probe state, sector observations, 121 visit
  records, and 12 event records.

## 2026-07-30

## Missions 11–13 - Constraint-Based Planning

Completed:

- Added JSON-backed Desired State defaults and SQLite-persisted overrides.
- Added typed production, resource-reserve, fuel, inventory, and travel goals.
- Completed the manufacturing planner rule.
- Converted manufacturing shortages into actionable mining requirements.
- Added ranked current-sector mining targets and Manny availability checks.
- Added fuel-reserve and free-capacity planning.
- Added deterministic shortest-path routing across FCC sector coordinates.
- Added travel blocker analysis for probe status, telemetry, and fuel.
- Reconstructed the durable galaxy before planning and exposed it through
  GalaxyService.
- Added quantities to planner dashboard output.

Verification:

- Added end-to-end planner tests for Missions 11, 12, and 13.
- Added Desired State serialization and persistence tests.
- Full suite passes with 48 tests.
- Live API v103 launch restored probe `762`, handled its cruising state without
  a sector snapshot, rebuilt history, and produced the expected travel and fuel
  recommendations without issuing game commands.

Next Session:

Mission 14 — Policy-Controlled Execution

- Map planner tasks to typed API commands.
- Require explicit player policy before mutations.
- Add dry-run, approval, idempotency, and action-journal safeguards.
- Begin multi-probe scheduling and message-driven coordination.

## 2026-07-30

## Mission 14 - Safe Execution Foundation

Completed:

- Added typed Manny craft, atomic-printer craft, mining, and movement commands.
- Added planner-to-command translation using reviewed API request shapes.
- Added explicit probe binding and just-in-time preflight validation.
- Added observe, approve, and automatic policy modes.
- Added a master live-execution intent, command allowlist, and cycle limit.
- Added stable command fingerprints and completed-action suppression.
- Migrated the Data Engine to schema version 2 with an action journal.
- Added a dry-run Command Preview to the dashboard.
- Closed SQLite connections deterministically.

Safety Boundary:

- The default policy is observe-only.
- Live execution is disabled.
- No command dispatcher exists.
- No game mutation can occur through this layer.

Next Session:

Mission 15 — Opt-In Automation Runtime

- Build the approval queue and emergency stop.
- Add a capability dispatcher behind the policy boundary.
- Refresh and revalidate immediately before every mutation.
- Record complete command lifecycle events.
- Replan after every terminal result.
