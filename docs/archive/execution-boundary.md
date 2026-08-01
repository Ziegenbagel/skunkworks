# Execution Boundary

## Status

Missions 14 and 19 are complete. Skunkworks can prepare, validate, approve,
dispatch, reconcile, and journal one policy-allowed command per execution cycle.
The shipped configuration remains observe-only with live execution disabled.

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
Approval / Risk Acknowledgement
    |
    v
Fresh World Refresh + Second Preflight
    |
    v
Per-Probe Execution Lease
    |
    v
Allowlisted Capability Dispatcher
    |
    v
Action Journal + Replan
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

The shipped policy is observe-only with live execution disabled. Enabling live
execution still requires an allowlisted command type and the selected mode's
approval requirements.

## Safety Guarantees

- Every command is bound to an explicit probe ID.
- The selected probe and World Model probe must match.
- Live telemetry and idle state are checked immediately before queueing.
- Manny commands require an existing, orderable Manny.
- Movement commands are validated as FCC coordinates and use one hop.
- Movement commands carry advisory hazard warnings from the selected route.
- Risk acknowledgement and outright risk refusal are separate policy choices.
- Stable fingerprints support retries and completed-action suppression.
- Proposed command state is appended to the SQLite action journal.
- Command preparation has no reference to mutation gateways.
- Dispatch refreshes the selected probe and repeats preflight validation.
- Command approval and hazard acknowledgement are independent.
- A durable emergency stop cancels execution before any gateway call.
- Short-lived per-probe leases prevent overlapping mutations.
- Completed fingerprints cannot be dispatched twice.
- Retryable timeouts, connection failures, rate limits, and server errors use
  bounded retry/cooldown handling.
- Every terminal execution result triggers replanning when a callback is
  configured.

## Remaining Automation Handoff

Later missions must add:

- A player-facing approval interface (Mission 24).
- Long-running multi-command scheduling and recovery (Missions 23 and 25).
- Broader command translation coverage after each command receives dedicated
  preflight rules.
