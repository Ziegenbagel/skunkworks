# Skunkworks Operator Manual

This directory is the maintained source for the Skunkworks user guide.

## Update contract

Any user-visible workflow, setting, control, safety behavior, or terminology change must update:

1. `build_manual.py` for the affected instructions or diagram legend.
2. `CHANGELOG.md` with the date and user-visible change.
3. The dashboard source screenshot when its layout materially changes.
4. The generated `Skunkworks_Operator_Manual.docx` after visual verification.

Build with the bundled Codex document runtime described in the document skill. The builder accepts a dashboard screenshot path through `SKUNKWORKS_GUIDE_SCREENSHOT`; otherwise it uses the current development screenshot configured in the script.

The manual deliberately distinguishes observed game data, Skunkworks recommendations, and commands that can modify the live game account.

