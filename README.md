# Skunkworks

> Configure your fleet. Define your objectives. Let Skunkworks handle the
> repetitive operations while you retain strategic control.

Skunkworks is a cross-platform mission-control and autonomous operations client
for the Von Neumann Game. It reads the official API, builds a persistent world
model, compares live state with player-defined goals, explains proposed work,
and dispatches only commands permitted by the selected execution and safety
policies.

## Current capabilities

- Live multi-probe selection, fleet status, resources, missions, production,
  logbooks, messages, alerts, and sector/galaxy visualization.
- Manual travel, scanning, inventory/container operations, Manny control,
  deuterium transfer, mining destinations, and movement cancellation.
- Desired quantities and 1–10 priorities for probes, tankers, Mannies,
  containers, SCUT relays, and transit beacons.
- Explainable manufacturing/mining planning with active-production accounting,
  priority resource reservations, and container-capacity reservations.
- Per-probe observe, approval, and automatic execution policies with allowlists,
  leases, refreshed preflight checks, and an emergency stop.
- Travel, fuel, cargo-detachment, depletion, depot, tanker, and round-trip
  logistics safeguards that warn without unnecessarily removing operator choice.
- Persistent SQLite history for the galaxy, sectors, probes, resources,
  operations, actions, messages, alerts, missions, and settings.
- Von Neumann Game API v103–v115 reviewed compatibility with forward-tolerant six-hour
  compatibility monitoring and safe pause on an unreviewed version.
- Native Qt/PySide desktop UI designed for macOS, Windows, and Linux, scaling
  from 1080p through 4K.

## Run Mission Control

Skunkworks currently requires Python 3.14 and the dependencies declared in
`pyproject.toml`.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
skunkworks
```

On Windows, activate with `.venv\Scripts\activate`. The first-launch wizard or
Settings page stores the game API key in the operating-system credential vault;
it is not written into project settings or logs.

For release downloads, platform-specific installation, source archives, and
upgrade instructions, see [Installing, Running, and Updating Skunkworks](docs/installing-and-updating.md).

## Safety model

Skunkworks never treats a plan as permission. Every live command passes through
fresh-state validation, normalization, safety review, execution policy,
allowlist, API compatibility, idempotency, and emergency-stop checks. Risk
profiles control warnings and acknowledgements while preserving allowed operator
decisions.

## Documentation

- [Documentation index](docs/README.md)
- [Operator Manual](docs/user-guide/Skunkworks_Operator_Manual.docx)
- [User-visible changelog](docs/user-guide/CHANGELOG.md)
- [Architecture](docs/architecture.md)
- [Reviewed API and game observations](docs/api-notes.md)
- [Planner and automation](docs/planner.md)
- [Logistics and safety](docs/logistics-and-safety.md)
- [Roadmap](docs/roadmap.md)
- [Engineering guide](docs/engineering-guide.md)
- [Version 1.0 release checklist](docs/release-checklist.md)
- [Capability matrix](docs/capability-matrix.md)
- [Installing and updating](docs/installing-and-updating.md)
- [Distribution license decision](docs/licensing-decision.md)
- [Private test-data workflow](docs/private-test-data.md)
- [Privacy](PRIVACY.md), [security](SECURITY.md), and [support](SUPPORT.md)
- [Discord release-post template](docs/discord-release-post.md)

Historical mission notes and superseded design packages are retained under
`docs/archive/` but are not current product contracts.

## Development checks

```bash
python -m pytest -q tests
pyside6-qmllint -I src/ui/qml src/ui/qml/App.qml
git diff --check
```

Live diagnostic scripts under `tools/` are intentionally separate from the
automated test suite because they access the real game service.

## Project status

The architecture, desktop interface, safety foundation, and controlled
automation runtime are implemented. Remaining 1.0 work focuses on long-running
autonomy/recovery, API parity testing, packaging/signing, migrations, and public
release hardening. See the [release roadmap](docs/roadmap.md) for the maintained
scope.

## Acknowledgements

Skunkworks is an independent companion project for the open-source
[Von Neumann Game](https://github.com/gnieark/Von-Neumann-Game).

## Source and license

Skunkworks publishes source for inspection and licenses official, unmodified
releases for individual personal, non-commercial use. Modification, derivative
distribution, redistribution of release files, commercial use, and reuse of
original application assets require prior written approval. Share the official
GitHub Releases link rather than copying an installer. See [LICENSE](LICENSE).
