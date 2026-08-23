# Distribution License Decision

This document identifies the owner's remaining legal choices. It is practical
release preparation, not legal advice.

## Owner's intended model

The current owner intent is **publicly viewable source with restricted reuse**:

- users may obtain and run official, unmodified Skunkworks releases;
- source may be inspected for trust, education, and issue reporting;
- editing, modification, derivative works, and distributing modified versions
  require prior written approval;
- original Skunkworks artwork, interface assets, documentation design, name, and
  logo may not be extracted or reused without prior written approval;
- third-party components and media remain governed by their own licenses.

This is a **source-available proprietary** model, not an open-source license.
Open-source licenses must permit modification and derived works. A custom
Skunkworks Source-Available License should be reviewed by a qualified lawyer
before public release.

Three owner decisions are still required for the final text:

1. Whether unmodified Skunkworks may be used for commercial purposes.
2. Whether users may redistribute an untouched official installer/source archive,
   or must always link recipients to the official GitHub release.
3. The legal copyright-holder name and jurisdiction/contact for written approvals.

Requiring downloads from the official GitHub Releases page is the cleanest way
to protect provenance, preserve notices, and keep users on supported builds.

## Standard alternatives considered

Publishing code on GitHub does not by itself grant others permission to copy,
modify, or redistribute it. Select one clear project license before 1.0:

| Choice | What it permits | Principal tradeoff |
|---|---|---|
| Apache License 2.0 | Broad use, modification, redistribution, and commercial use; includes an express patent grant | Others may distribute closed-source forks if they preserve required notices |
| MIT License | Very short permissive grant for broad reuse | No express patent grant and closed-source forks are allowed |
| GNU GPL v3 | Redistribution and modified distributed versions must remain under GPL with corresponding source | Some companies and proprietary integrations will avoid it |
| Proprietary / all rights reserved | Users receive only the permissions written in a custom end-user license | Public collaboration and redistribution are restricted; custom drafting deserves legal review |

These standard licenses do not implement the current approval-before-modification
intent. GPL requires modification rights, while Apache and MIT additionally
permit proprietary forks. They remain alternatives only if the owner later
chooses a conventional open-source model.

Avoid a custom "non-commercial" or "source available" license unless that is a
deliberate business requirement; such terms are not standard open-source terms
and create more interpretation and compatibility work.

## Third-party software

The project license does not replace dependency obligations. Release packaging
must ship exact license and notice texts for PySide6/Qt, Requests, python-dotenv,
keyring, their bundled transitive components, and any build-time component that
requires redistribution notices. PySide6 is offered under LGPL/GPL/commercial
terms; the selected distribution method must satisfy the applicable Qt terms.

## Artwork, audio, documentation, and trademarks

Decide whether original artwork and documentation use the same project license
or separate terms such as Creative Commons. Preserve the existing audio credits
and source licenses. Confirm that the Skunkworks name, logo, screenshots, and
references to the Von Neumann Game do not imply endorsement. A short independent-
project trademark disclaimer should accompany public downloads.

## Privacy and support policy

Before publishing, decide:

- the public security-report contact or private advisory channel;
- the support lifetime for 1.0 releases;
- whether crash reports will remain local-only (the current behavior);
- whether anonymized screenshots replace all live-account screenshots;
- whether old Git history containing live observations must be rewritten before
  the repository becomes public.

The final release should record the chosen source license, asset/document terms,
copyright holder name, and year consistently in the repository and package.
