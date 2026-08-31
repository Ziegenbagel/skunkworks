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

Each user-visible change merged to `develop` also adds a concise candidate to
`docs/development-release-log.md`. During promotion, validate those candidates
against the finished application and rewrite the approved items as
operator-facing bullets in `RELEASE_NOTES.md`. Never pass the development log
directly to the public release workflow, and do not copy its internal-support
notes into public notes as implementation detail.

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

This owner checkout uses the preserved private test profile at
`private/test-data`. Always set `SKUNKWORKS_HOME` to that same directory when
launching this checkout. Omitting it selects the platform default profile and
can make the development copy appear to have reset settings and history even
though the preserved profile is intact. A clean platform profile correctly
starts in Observe Only; do not reconfigure it as a substitute for selecting the
intended test profile.

The preserved private profile points to the existing accumulated development
database and retains its saved policy files. A verified backup is still
required before testing persistence, migration, compaction, or restore changes.

Update and launch the development branch on macOS or Linux:

```bash
cd /absolute/path/to/Skunkworks
git switch develop
git pull --ff-only origin develop
uv sync --locked
SKUNKWORKS_HOME="$PWD/private/test-data" uv run --no-sync python -m src.ui.app
```

On Windows PowerShell:

```powershell
Set-Location C:\absolute\path\to\Skunkworks
git switch develop
git pull --ff-only origin develop
uv sync --locked
$env:SKUNKWORKS_HOME = "$PWD\private\test-data"
uv run --no-sync python -m src.ui.app
```

`uv` owns this repository's `.venv`; that environment may intentionally omit
`pip`. Do not assume `python -m pip` is available inside it. The development
launch deliberately runs `src.ui.app` from the checked-out repository instead
of relying on an editable installation's generated console launcher. Run
`uv sync --locked` again after pulling dependency changes. `--no-sync` on the
launch command prevents `uv run` from silently changing the environment while
starting the application.
Keep the `SKUNKWORKS_HOME` assignment on every development launch; it is the
identity of the selected writable profile, not an installation option.

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
