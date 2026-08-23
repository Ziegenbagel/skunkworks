# Public Screenshot Privacy Review

Status: PENDING SYNTHETIC RECAPTURE

The current manual screenshots were intentionally supplied during development,
but several visibly contain live probe names, coordinates, resource quantities,
object identifiers, and operational history. They must not be included in the
public 1.0 manual or packages under the project's private-data policy.

Required replacement workflow:

1. Launch Skunkworks against a synthetic demo service/profile.
2. Use names such as Example Hub, Example Explorer, and Example Manny 001.
3. Use synthetic object IDs, coordinates, messages, resource quantities, and
   timestamps that do not correspond to the owner's account.
4. Recapture every file under `assets/screenshots/` plus the numbered dashboard
   and settings images derived from them.
5. Rebuild the DOCX and PDF, visually inspect every rendered page, then change
   this status to `Status: APPROVED SYNTHETIC DATA`.

Cropping the focused-probe header alone is insufficient because live values also
appear inside production, logbook, galaxy, navigation, and settings panels.
