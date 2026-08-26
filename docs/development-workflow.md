# Development and Release Branch Workflow

This document is the repository authority for separating public releases from
unfinished roadmap work. Chat history is supporting context only.

## Permanent branches

- `main` is the stable public line. It contains released code, release-ready
  documentation, and urgent fixes. Unfinished roadmap features do not begin on
  or merge directly into `main`.
- `develop` is the integration line for the next release. Features merge here
  only after their focused tests pass. The complete offline suite must pass
  before `develop` is promoted to `main`.
- `codex/<feature-name>` is the default feature-branch form. Create each feature
  from `develop`, keep its commits scoped, and merge it back into `develop`
  after review and testing.

Release flow:

```text
codex/<feature> -> develop -> main -> vX.Y.Z tag -> public packages
```

Urgent patch flow:

```text
main -> codex/hotfix-<name> -> main -> patch tag
                              \-> merge the fix back into develop
```

## Public-package boundary

The public release workflow runs only for `v*` tags. Create release tags only
from an approved commit on `main`. Ordinary pushes to `develop` and feature
branches run CI but must not publish a GitHub Release.

The manually dispatched release-candidate workflow may be run against
`develop` or a feature branch to create clearly labeled, unpublished test
artifacts. Use a development label such as `1.1.0-dev.3`; never reuse a public
version number for a test artifact.

## Testing without losing operator data

Application upgrades must preserve the platform user-data directory. Never put
live databases, credentials, snapshots, policy files, backups, or logs in the
repository or a package payload, and never delete them as part of an update.

There are two supported local test arrangements:

1. For ordinary compatibility testing, launch the development checkout while
   retaining the normal user-data location. Make a verified backup first when a
   change touches persistence or migrations.
2. For isolated or destructive testing, copy a verified backup into a separate
   directory and launch with `SKUNKWORKS_HOME` pointed at that directory. This
   keeps experiments from modifying the operator's normal profile.

Example isolated launch:

```bash
SKUNKWORKS_HOME=/absolute/path/to/skunkworks-test-data python -m src.ui.app
```

Do not commit either location. A feature that changes the database schema must
also prove that the previous public version can be upgraded without losing
settings, roles, operations, galaxy history, or action history.

## Launching the 1.1 development line

The development checkout uses the normal platform user-data location unless
`SKUNKWORKS_HOME` is explicitly set. Therefore the operator can test 1.1 with
the existing accumulated profile, but must create a verified backup before
testing persistence, migration, compaction, or restore changes.

Update and launch the development branch on macOS or Linux:

```bash
cd /absolute/path/to/Skunkworks
git switch develop
git pull --ff-only origin develop
uv sync --locked --no-editable
uv run --no-sync skunkworks
```

On Windows PowerShell:

```powershell
Set-Location C:\absolute\path\to\Skunkworks
git switch develop
git pull --ff-only origin develop
uv sync --locked --no-editable
uv run --no-sync skunkworks
```

`uv` owns this repository's `.venv`; that environment may intentionally omit
`pip`. Do not assume `python -m pip` is available inside it. Python 3.14 skips
hidden `.pth` files, including the file currently produced by setuptools for an
editable install. `uv sync --locked --no-editable` installs the actual package
and launcher into the environment without relying on that skipped file. Run it
again after pulling source changes. `--no-sync` on the launch command prevents
`uv run` from silently changing the project back to an editable installation.

The footer must show a `1.1.0.dev...` version while this branch is under
development. If it shows a public `1.0.x` version, stop and confirm the selected
branch and editable installation before testing new behavior.

## Working procedure

1. Begin new roadmap work from an up-to-date `develop`.
2. Create one `codex/<feature-name>` branch per independently reviewable change.
3. Read the applicable engineering guardrails and architecture/planner sections.
4. Add behavioral regression tests and run focused tests during implementation.
5. Run `python -m pytest -q tests` and `python -m tools.release_readiness` before
   merging the feature into `develop`.
6. Test the integrated `develop` build with a safe data arrangement.
7. When the release is approved, merge `develop` into `main`, update release
   metadata, rerun the release checklist, and create the release tag.
8. After a hotfix ships from `main`, merge that same fix back into `develop` so
   future releases cannot erase it.
