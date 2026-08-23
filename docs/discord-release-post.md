# Skunkworks Discord Release Post

Copy the text below into the Von Neumann Game community-tools channel. Replace
`<version>` with the published release number and remove the pre-release warning
only after the release checklist is complete.

---

## SKUNKWORKS `<version>` — Mission Control for Von Neumann Game

Skunkworks is a cross-platform desktop companion for managing a growing Von
Neumann Game fleet. It combines live fleet information, manual controls, safety
checks, persistent history, and optional goal-driven automation in one mission
control interface.

**Highlights**

- Fleet, probe, resource, mission, production, message, alert, and logbook views
- Interactive sector navigation and a persistent 3D galaxy map
- Manual travel, scanning, crafting, mining, repair, cargo, container, SCUT,
  transfer, and supported infrastructure controls
- Production and fleet targets with priorities and explainable waiting reasons
- Probe roles for hubs, explorers, transports, deuterium tankers, and reserves
- Observe Only, Require Approval, and Automatic execution modes
- Per-command allowlists, fresh-state validation, fuel/cargo safeguards, API
  compatibility checks, and an emergency stop
- Local SQLite history and diagnostic tools; the API key is stored in the
  operating-system credential vault

**Download, source, release notes, and updates**

https://github.com/Ziegenbagel/skunkworks/releases/latest

Project page and source:
https://github.com/Ziegenbagel/skunkworks

Use the package matching your operating system from GitHub Releases. Source
users can follow the repository's Installing, Running, and Updating guide.
Please use an official, named release rather than an unreviewed moving branch
with a valuable game account.

**First launch**

1. Install and open Skunkworks, then enter your Von Neumann Game API key in the
   first-launch walkthrough. The key is saved in your operating-system vault.
2. Test the connection and confirm that the expected account and focused probe
   are shown.
3. Leave execution mode on **Observe Only** while Skunkworks performs its first
   refresh and builds the local view of your fleet.
4. Review Mission Control, Fleet, Resources, Production, Safety, and the
   planner's waiting reasons. A first galaxy-map population can take longer than
   an ordinary refresh.
5. In Settings, configure the focused probe's targets, resource floors, fuel
   floor, minimum free capacity, repair threshold, and probe role. Settings are
   probe-specific, so repeat this for each probe you intend to automate.
6. Read proposed commands in Observe Only. If desired, move to **Require
   Approval** first and confirm a few representative orders manually.

**Before enabling Automatic mode**

- Verify that the focused probe is the probe you intend to configure.
- Confirm target quantities and priorities; Priority 1 is highest.
- Confirm resource, fuel, free-capacity, repair, and travel-safety settings.
- Assign and review any transport, tanker, reserve, or explorer routes.
- Enable only the command allowlist categories you actually want automated.
- Check that **Allow Skunkworks to Send Game Orders** reflects your intent and
  choose a conservative maximum-orders-per-cycle value.
- Read every yellow waiting reason or warning and resolve anything unexpected.
- Confirm the detected game API is supported and the network is connected.
- Keep the emergency **STOP** control in mind. Automatic mode remains governed
  by safety checks, but it can send real game orders without another click.

Start conservatively: Observe Only → Require Approval → Automatic. Targets and
allowlists are permission boundaries, so recheck them after changing probe
roles, routes, inventory layout, or major fleet goals.

**Bugs, suggestions, and feedback**

Please include the Skunkworks version, operating system, game API version,
focused probe role, execution mode, exact time, reproduction steps, expected
result, and observed result. Refresh Diagnostics and the planner's waiting
reason are especially helpful.

- GitHub issues: https://github.com/Ziegenbagel/skunkworks/issues
- Discord: **@Ziegenbagel**
- Email: **ziegenbagel.gaming@gmail.com**

Never post an API key. Inspect logs or diagnostic bundles before sharing them;
they may contain probe names, messages, coordinates, inventory, or other private
game information.

Skunkworks is an independent community companion and is not the Von Neumann
Game service itself.

---
