# Execution Boundary

## Status

Mission 14 is complete as a pre-automation foundation. Skunkworks can prepare,
validate, classify, display, and journal commands, but it cannot dispatch them.

## Flow

```text
Planner Task
    |
    v
TaskCommandTranslator
    |
    v
Typed Command
    |
    v
PreflightValidator
    |
    v
ExecutionPolicy
    |
    v
Dry-Run Command Queue
    |
    v
Action Journal

No API mutation dispatcher exists yet.
```

## Supported Prepared Commands

- Manny crafting
- Atomic-printer crafting
- Manny mining
- One-hop FCC probe movement

Only planner tasks with no constraints can become commands. Advisory tasks,
blocked tasks, snapshot refreshes, inventory warnings, and waiting tasks remain
planner output only.

## Policy

`config/execution_policy.json` defines:

- `mode`: `observe`, `approve`, or `automatic`
- `liveExecutionEnabled`: master execution intent
- `allowedCommandTypes`: automatic-mode allowlist
- `maxCommandsPerCycle`: queue safety limit

The shipped policy is observe-only with live execution disabled. Changing the
file cannot execute a command because no dispatcher exists.

## Safety Guarantees

- Every command is bound to an explicit probe ID.
- The selected probe and World Model probe must match.
- Live telemetry and idle state are checked immediately before queueing.
- Manny commands require an existing, orderable Manny.
- Movement commands are validated as FCC coordinates and use one hop.
- Stable fingerprints support retries and completed-action suppression.
- Proposed command state is appended to the SQLite action journal.
- Command preparation has no reference to mutation gateways.

## Automation Handoff

The future automation runtime must add:

- An explicit approval interface.
- A dispatcher mapping each command type to its existing capability gateway.
- Just-in-time world refresh and a second preflight.
- Lifecycle events for approved, started, succeeded, failed, and cancelled.
- API retry, cooldown, rate-limit, and emergency-stop controls.
- Replanning after every completed or rejected action.
