# Third-Party Notices

Skunkworks runtime dependencies currently include:

| Component | Installed release audited | License expression |
|---|---:|---|
| PySide6 | 6.11.1 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| Requests | 2.34.2 | Apache-2.0 |
| python-dotenv | 1.2.2 | BSD-3-Clause |
| keyring | 25.7.0 | MIT |

Development-only dependencies include Pillow 12.3.0 (MIT-CMU), pytest 9.1.1
(MIT), and pytest-qt 4.5.0 (MIT).

This inventory is a release-preparation aid, not a substitute for the license
texts shipped by each dependency. The packaging build must collect the exact
notices and license files from the locked artifacts it distributes, including
transitive dependencies and Qt components. Artwork and audio provenance must be
checked separately against the asset manifest before release.

The Skunkworks Source-Available Personal Use License applies only to rights held
by the Skunkworks copyright holder. It does not replace or narrow any permission
granted directly by the third-party licenses above or by the licenses recorded
in `src/ui/assets/audio/AUDIO_LICENSES.md`.
