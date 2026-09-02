# Skunkworks Operator Manual

This directory is the maintained source for the Skunkworks user guide.

## Update contract

Any user-visible workflow, setting, control, safety behavior, or terminology change must update:

1. `build_manual.py` for the affected instructions or diagram legend.
2. `CHANGELOG.md` with the date and user-visible change.
3. Before a major release moves from `develop` to `main`, every affected
   synthetic screenshot whose displayed UI or behavior changed during the cycle.
4. At that same promotion gate, the generated
   `Skunkworks_Operator_Manual.docx` after visual verification.

Build with the bundled Codex document runtime described in the document skill. The builder accepts a dashboard screenshot path through `SKUNKWORKS_GUIDE_SCREENSHOT`; otherwise it uses the repository-owned synthetic capture.

Public screenshots are generated from the real QML with the offline fictional
profile in `tools/capture_synthetic_manual.py`. The harness uses a temporary
SQLite database and does not connect to the game API or read private test data.
Use its named tab and scroll-target options when updating dense Settings or
Manual Control panels so captures remain deterministic.

At the major-release promotion gate, never retain a screenshot that shows
superseded controls, labels, states, or behavior. Recreate the affected image
from the real QML and fictional offline profile, then render and inspect the
complete manual so its explanation, caption, and screenshot agree.

The manual deliberately distinguishes observed game data, Skunkworks recommendations, and commands that can modify the live game account.
