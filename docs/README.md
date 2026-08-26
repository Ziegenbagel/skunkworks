# Skunkworks Documentation

This directory intentionally keeps a small canonical set. If two documents
disagree, the source code and current official game API remain authoritative,
followed by the documents below.

## Operator documentation

- `user-guide/Skunkworks_Operator_Manual.docx` — illustrated user manual.
- `user-guide/CHANGELOG.md` — user-visible changes and manual revisions.
- `discord-release-post.md` — copy-ready community release announcement,
  first-launch checklist, and public support contacts.

## Product and engineering documentation

- `architecture.md` — runtime layers, world model, persistence, capabilities,
  and component ownership.
- `api-notes.md` — reviewed game API contract and verified game observations.
- `planner.md` — desired state, priority allocation, command preparation, and
  automation execution.
- `logistics-and-safety.md` — travel hazards, resources, depots, transport
  cycles, tanker rules, and operator risk policy.
- `engineering-guide.md` — coding, testing, review, and documentation rules.
- `development-workflow.md` — stable, integration, feature, hotfix, test-data,
  and public-package branch boundaries.
- `roadmap.md` — remaining work to 1.0 and the post-1.0 backlog.
- `release-checklist.md` — repository, data, live-service, and packaging gates.
- `capability-matrix.md` — release-level map of observed, manual, and automated controls.
- `installing-and-updating.md` — package downloads, source setup, and upgrades.
- `licensing-decision.md` — owner choices for source, assets, and distribution.
- `private-test-data.md` — retaining private fixtures without publishing them.
- `repository-publication.md` — history cleanup and clean release staging.

## Archive

`archive/` contains superseded design packages, detailed component notes, and
the chronological development diary. Archive files preserve rationale but are
not current product contracts and should not be linked from the live UI.

## Maintenance rule

User-visible behavior changes update the Operator Manual and changelog.
Architecture or API changes update the applicable canonical reference. Completed
session narratives belong in the archive, not in new top-level documents.
