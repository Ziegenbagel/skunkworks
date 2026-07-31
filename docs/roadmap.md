# Skunkworks Release Roadmap

## Status

This is the canonical Skunkworks roadmap as of 2026-07-30.

Missions 1–18 are complete. Development continues with Mission 19 and targets
the 1.0 release at Mission 26.

This roadmap reconciles:

- The original Skunkworks development plan.
- The Skunkworks Brainstorming Guide.
- The reviewed Von Neumann Game API and source.
- The capabilities currently implemented in this repository.

Mission numbers and release gates should only change through an explicit
roadmap revision. New ideas belong in the post-1.0 backlog unless they are
required for safety, data integrity, API parity, or a listed 1.0 release gate.

## Product Direction

Skunkworks is an explainable mission-planning and fleet-operations platform.

The player defines objectives and acceptable risk. Skunkworks observes the
game, constructs a durable operational model, plans operations, requests any
required approvals, executes permitted actions, and explains the result.

The application core must remain independent of the graphical interface so
future background, tray, headless, and remote interfaces do not require a
backend redesign.

## Completed Foundation

### Missions 1–10

- API, snapshots, dashboard, and developer tools.
- Intelligence, World Model, and World Builder.
- Knowledge and recipe systems.
- Operational services.
- Planner, task, rule, priority, and explanation foundations.

### Missions 11–13

- Manufacturing intelligence.
- Persistent Desired State.
- Constraint-based production, mining, fuel, inventory, and travel planning.
- Multi-probe selection and durable galaxy context.

### Mission 14

- Typed dry-run commands.
- Preflight validation.
- Execution policies.
- Idempotency fingerprints and action journal.

### Missions 15–16

- Configurable advisory travel safety.
- Collision, container, integrity, black-hole, unknown-sector, and
  forgotten-Manny warnings.
- Direct, segmented, and SCUT-aware route comparison.

### Missions 17–18

- Resource depletion and finite-field warnings.
- Replacement-source discovery.
- Hub, miner, and transport logistics blueprints.

## Roadmap to 1.0

### Mission 19 — Controlled Automation Runtime

Goal: safely complete the first real mutation through the existing execution
boundary.

- Approval queue.
- Separate command approval and hazard acknowledgement.
- Emergency stop.
- Short-lived execution leases.
- Allowlisted capability dispatcher.
- Just-in-time telemetry refresh and second preflight.
- One-command initial execution cycle.
- Proposed, approved, started, succeeded, failed, cancelled, and expired
  lifecycle records.
- Timeout, cooldown, retry, and rate-limit handling.
- Replanning after every terminal result.
- Observe, approval-required, and automatic modes.

Release gate: one crafting, mining, or movement command can be approved,
dispatched, reconciled, and journaled without allowing uncontrolled execution.

### Mission 20 — Durable Operations and Fleet Logistics

Goal: plan objectives as resumable operations rather than disconnected tasks.

- Add a durable `Operation` model containing:
  - objective and assigned assets;
  - state and current step;
  - pending steps;
  - pause and resume conditions;
  - completion and failure conditions.
- Maintain separate active-game and planned-operation queues.
- Reconcile operations with live state after restart.
- Add player-owned probe and Manny roles:
  - hub;
  - miner;
  - transport;
  - explorer;
  - builder/support;
  - unassigned.
- Add transport capacity, pickup, storage transfer, and delivery-cycle plans.
- Add hub reserve and shipment goals.
- Add ordered and weighted production priorities with conditional overrides.
- Prevent conflicting asset assignments.
- Refresh replacement deposits before deployment.

Initial operation templates:

- Expand Mining.
- Establish Mining Depot.
- Fuel Recovery.
- Build or Expand Hub.
- Recover Lost Assets.
- Production Campaign.

Release gate: Skunkworks can explain, persist, pause, resume, and coordinate a
complete source-to-hub logistics operation.

### Mission 21 — Manny, Container, and Depot Intelligence

Goal: make workers and persistent infrastructure first-class operational
domains.

- Add a normalized Manny domain and dedicated `MannyService`.
- Answer total, idle, available, deployed, mining, manufacturing, assigned,
  progress, and next-completion questions.
- Track worker utilization, bottlenecks, recall, recovery, and reassignment.
- Add container and detached-storage intelligence.
- Treat detached containers as world assets that can outlive their source
  probe.
- Model a Mining Depot as a logical asset composed of:
  - asteroid;
  - hidden or detached storage;
  - mining Mannys;
  - transport capacity;
  - servicing probe or hub.
- Track depot throughput, fill state, container rotation, lifetime production,
  idle time, maintenance, and depletion.
- Use stable game identifiers internally and public asteroid names in
  player-facing reports.
- Keep deuterium in its distinct fuel pipeline unless the game adds compatible
  transportable storage.
- Recommend depot construction using expected time savings and break-even
  estimates.

Release gate: Skunkworks can determine whether the fleet has sufficient
workers, storage, transport, and source longevity for every planned industrial
operation.

### Mission 22 — Messaging, Missions, and Exploration Operations

Goal: coordinate narrative and operational objectives through the same mission
system.

- Add `MessagingService` and inbox/outbox workflows.
- Synchronize messages, alerts, warnings, missions, and logbook pages.
- Track unread, acknowledged, linked, and priority events.
- Add mission acceptance, progress, and abandonment controls.
- Extract coordinates and objectives from messages without automatically
  solving or responding to unreviewed narrative puzzles.
- Add exploration operation templates:
  - frontier exploration;
  - destination explorer;
  - resource search;
  - investigation;
  - rescue and recovery.
- Add route scoring for safety, discovery value, fuel opportunities, SCUT
  coverage, hazards, and configurable detour budgets.
- Pause for fuel, hazards, quests, or recovery and resume the original
  objective afterward.
- Add search-corridor planning for destroyed probes and abandoned Mannys.
- Support event-driven replanning and coordination.

Release gate: a probe can pursue a long-range exploration objective, survive
interruptions, retain mission intent, and resume safely.

### Mission 23 — Refresh Scheduler, Prediction, and Operational Health

Goal: remain responsive and accurate without wasteful polling.

- Centralize API refresh decisions outside the UI.
- Honor `nextUsefulRefreshDelayMs`.
- Prioritize the focused probe and reduce background-probe polling.
- Refresh immediately after player or automation mutations.
- Maintain local countdowns, progress, ETAs, and confidence levels.
- Predict:
  - task completion;
  - resource consumption and exhaustion;
  - production completion;
  - transport throughput;
  - fuel reserves;
  - inventory saturation;
  - Manny utilization;
  - probe integrity trends.
- Detect prediction drift and compare forecasts with actual outcomes.
- Add fleet readiness, bottleneck, stale-data, and operational-health
  assessments.
- Keep observed mechanics and hypotheses explicitly separated from verified
  rules.

Release gate: the UI stays current through local prediction and reasoned
refreshes, while Skunkworks warns before major operational constraints become
failures.

### Mission 24 — Mission Control User Interface

Goal: provide a polished, complete player-facing operations console.

- Persistent probe selector and fleet overview.
- Probe, inventory, Manny, container, storage, production, and role controls.
- Desired State, production-priority, safety-policy, and automation editors.
- Approval queue, command preview, operation queue, and action history.
- Sector and galaxy maps built from durable FCC observations.
- Resource, route, SCUT, hazard, discovery, infrastructure, mission, and stale
  data overlays.
- Messaging, missions, alerts, game logbook, and Skunkworks archive views.
- Preserve the game logbook as player-authored notes while keeping generated
  operational reports in the separate Skunkworks archive.
- Upcoming-events timeline and away/command briefing.
- Human-friendly durations, local-time completion estimates, and consistent
  resource precision.
- Progressive disclosure and context links between entities, events, and maps.
- Clear disconnected, stale, blind, limited-telemetry, rate-limited, paused,
  and emergency-stop states.

Design requirements:

- Information first; graphics amplify meaning.
- Aerospace operations-console identity.
- Matte dark surfaces with restrained cyan/blue structure.
- Copperplate Bold reserved for major titles.
- Readable sans-serif body text and monospace technical data.
- Color and motion communicate state.
- Reusable design system, SVG icon language, and window archetypes:
  Data Pad, Inspector, Alert Console, and Navigation Console.
- Core behavior must not depend on the GUI.

Release gate: every supported routine game operation can be inspected,
planned, approved, and controlled without editing configuration files or
requiring the game website.

### Mission 25 — Continuous Autonomy, Recovery, and API Parity

Goal: safely extend the one-command runtime into durable fleet operations.

- Durable scheduler and fleet-wide work queue.
- Dependency-aware concurrency.
- One active execution lease per assigned asset.
- Restart, crash, and ambiguous-result recovery.
- Stale approval expiration.
- Pause globally or by probe, role, operation, or command type.
- Human override at every level.
- State reconciliation after external game changes.
- Away-summary and operational-archive event generation.
- Meaningful exploration, discovery, production, logistics, and incident
  reports rather than raw event spam.
- Full public API capability audit.
- Capability matrix: observable, plannable, executable, intentionally
  unsupported, or awaiting verified mechanics.
- API migration strategy and fixture-backed compatibility tests.
- Offline/read-only degraded mode.
- Data Engine and configuration backup and migration tools.

Release gate: Skunkworks can run approved operations unattended and recover
safely from restarts, API errors, rate limits, and unexpected state changes.

### Mission 26 — 1.0 Release Hardening

Goal: make the release reproducible, supportable, and trustworthy.

- End-to-end tests with a non-destructive or dedicated test account.
- Dispatcher contract tests for every allowed mutation.
- Failure-injection, emergency-stop, restart, and reconciliation tests.
- Safety-profile and policy validation.
- Database migration and backup/restore tests.
- Performance tests with large fleets and galaxy histories.
- Secrets, privacy, log-redaction, and dependency audit.
- Installation, upgrade, first-run setup, and clean-machine verification.
- User guide, troubleshooting guide, architecture, API, safety, and automation
  documentation.
- Changelog, license, packaging, and release artifacts.
- Release-candidate soak period.

Release gate: no critical defects, no unexplained mutations, successful
recovery tests, complete documentation, and reproducible installation.

## 1.0 Definition of Done

Skunkworks 1.0 must:

- Observe all supported game domains through explicit probe context.
- Preserve a durable operational and historical model.
- Let the player define goals, priorities, roles, and risk tolerance.
- Generate explainable, resumable Operations.
- Execute only policy-permitted and freshly validated actions.
- Warn clearly without silently forbidding player-authorized risk.
- Recover safely from restarts and uncertain API outcomes.
- Provide routine game controls through Mission Control.
- Keep the core independent from the UI.
- Pass the Mission 26 release gates.

## Post-1.0 Backlog

### Version 1.1 — Efficient Background Operations

- Low Usage Mode.
- Background polling and reduced rendering.
- Persistent local notifications.
- Richer away summaries and archive search.
- Additional mining-depot ROI and historical analytics.
- User annotations and research archive.

### Version 1.2 — Desktop Continuity

- System tray mode.
- Continue automation while the main window is hidden.
- Desktop notification controls.
- Saved workspace layouts.
- Operation synchronization between trusted devices.

### Version 1.x — Strategic Intelligence

- Automated SCUT network design.
- Hub-placement optimization.
- Fuel-station and infrastructure network planning.
- Advanced explorer campaigns and frontier coverage optimization.
- Civilization-contact and quest reward analysis.
- Economic what-if simulation.
- Adaptive production priorities.
- Predictive maintenance and probe replacement planning.
- Plugin/mod architecture.

### Version 2.0 — Headless and Remote Operations

- Headless service.
- Remote dashboard or web interface.
- Multi-device command center.
- Long-running server deployment.
- Advanced empire-wide autonomy.
- Cross-player or alliance coordination where supported.

## Deferred or Conditional Ideas

The following require verified game support before automation:

- Waiting for or deliberately triggering emergency wandering deuterium.
- Automated narrative puzzle solving.
- Exact destroyed-probe or abandoned-Manny position estimation.
- Fuel-container logistics not exposed by the game.
- Repair and maintenance predictions without sufficient telemetry.

They may be researched and displayed as hypotheses, but must not become
automatic behavior until verified.
