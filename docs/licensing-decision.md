# Distribution License Decision

This document identifies the owner's remaining legal choices. It is practical
release preparation, not legal advice.

## Source-code license

Publishing code on GitHub does not by itself grant others permission to copy,
modify, or redistribute it. Select one clear project license before 1.0:

| Choice | What it permits | Principal tradeoff |
|---|---|---|
| Apache License 2.0 | Broad use, modification, redistribution, and commercial use; includes an express patent grant | Others may distribute closed-source forks if they preserve required notices |
| MIT License | Very short permissive grant for broad reuse | No express patent grant and closed-source forks are allowed |
| GNU GPL v3 | Redistribution and modified distributed versions must remain under GPL with corresponding source | Some companies and proprietary integrations will avoid it |
| Proprietary / all rights reserved | Users receive only the permissions written in a custom end-user license | Public collaboration and redistribution are restricted; custom drafting deserves legal review |

For an open project where continued openness matters, **GPL-3.0-only** is the
clearest fit. For the widest adoption and contribution surface, **Apache-2.0**
is the stronger permissive default because it includes patent terms. MIT is
reasonable when brevity matters more than the additional Apache terms.

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
