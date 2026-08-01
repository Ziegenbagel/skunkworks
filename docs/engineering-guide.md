# Engineering Guide

This is the canonical contributor standard.

## Architecture rules

- Keep HTTP construction in API gateways, normalization in intelligence, state
  in the world/data layers, questions in operational services, decisions in the
  planner, and mutations behind the execution boundary.
- Require explicit probe IDs for probe-scoped work.
- Prefer composition and small vertical slices over cross-layer shortcuts.
- Keep game facts separate from observations and from configurable policy.

## Planning and safety rules

- Every proposed command explains its goal, evidence, resource claims, and
  blockers.
- Refresh, normalize, safety-check, allowlist, and lease a command immediately
  before dispatch.
- Preserve operator choice for acknowledged risks while blocking invalid,
  stale, incompatible, or emergency-stopped execution.

## Code and tests

- Use descriptive domain names and small single-purpose services.
- Add regression coverage for every bug and contract change.
- Test pure rules without network access; isolate live API diagnostics from
  pytest collection.
- Run the full `tests/` suite, QML lint for UI changes, and `git diff --check`.
- Never log credentials or infer undocumented API behavior as fact.

## Documentation

- Update existing canonical documents instead of creating another mission or
  feature note.
- Update the Operator Manual and changelog for user-visible behavior.
- Record verified API facts in `api-notes.md`; label uncertain behavior as a
  hypothesis.
- Move completed design packages and chronological session notes to `archive/`.

## Release discipline

Support Windows, macOS, and Linux together. A release requires compatible API
validation, safe upgrade behavior, signed/packaged runtime testing, accessibility
and scaling checks, and a recoverable migration path for local data.
