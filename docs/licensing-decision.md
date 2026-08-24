# Distribution License Decision

This document identifies the owner's remaining legal choices. It is practical
release preparation, not legal advice.

## Selected model

On 2026-08-23, the owner selected the **GNU General Public License version 3
only (GPL-3.0-only)** for Skunkworks.

- users may run, inspect, modify, and redistribute Skunkworks;
- distributed modified versions must remain under GPLv3 and include the
  corresponding source;
- applicable copyright, attribution, license, and warranty notices must be
  preserved;
- modified versions must prominently state that they were changed and provide a
  relevant date;
- third-party components and media remain governed by their own licenses.

This is an open-source, strong-copyleft model. GPLv3 permits modification and
redistribution; it does not support an approval-before-modification restriction.

The owner decisions recorded on 2026-08-23 are:

1. The project is licensed under GPLv3 only.
2. The copyright holder and original creator is Christopher Ziegenhagel, also
   known as Ziegenbagel.
3. The application will display creator, copyright, GPLv3, no-warranty, and
   independent-project notices.

The official GitHub Releases page remains the recommended download source, but
GPLv3 recipients may redistribute compliant copies. These choices are
implemented in the root `LICENSE` and release documentation.

## Standard alternatives considered

Publishing code on GitHub does not by itself grant others permission to copy,
modify, or redistribute it. Select one clear project license before 1.0:

| Choice | What it permits | Principal tradeoff |
|---|---|---|
| Apache License 2.0 | Broad use, modification, redistribution, and commercial use; includes an express patent grant | Others may distribute closed-source forks if they preserve required notices |
| MIT License | Very short permissive grant for broad reuse | No express patent grant and closed-source forks are allowed |
| GNU GPL v3 | Redistribution and modified distributed versions must remain under GPL with corresponding source | Some companies and proprietary integrations will avoid it |
| Proprietary / all rights reserved | Users receive only the permissions written in a custom end-user license | Public collaboration and redistribution are restricted; custom drafting deserves legal review |

GPLv3 was selected because it requires distributed derivatives to preserve the
same software freedoms and provide corresponding source.

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
