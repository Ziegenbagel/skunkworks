# Installing, Running, and Updating Skunkworks

## Recommended public downloads

The official distribution channel is the repository's GitHub Releases page:

`https://github.com/Ziegenbagel/skunkworks/releases/latest`

Version 1.0 provides checksum-verifiable unsigned portable archives:

| Platform | Download |
|---|---|
| macOS Apple silicon | `Skunkworks-v<version>-macOS-arm64-unsigned.zip` |
| macOS Intel | `Skunkworks-v<version>-macOS-x86_64-unsigned.zip` |
| Windows 10/11 x64 | `Skunkworks-v<version>-Windows-x64-unsigned.zip` |
| Linux x86_64 | `Skunkworks-v<version>-Linux-x86_64-unsigned.zip` |

Every release also provides `SHA256SUMS.txt`, final release notes, and a curated
source archive. GitHub's stable latest-release URL is what
the application's **Check for Updates** button opens. Updates are intentionally
manual in 1.0: download the newer package, stop Skunkworks, back up the
database, and install the new version. Skunkworks must not silently replace its
own executable.

### macOS

Download and extract the ZIP matching the Mac processor. Move only
`Skunkworks.app` into Applications; the release documents and source archive do
not belong in Applications. Version 1.0 is not Developer ID signed or notarized,
so macOS may require the operator to confirm opening it. For the API key's
Keychain request, temporary **Allow** applies only to that launch; **Always
Allow** persists the authorization for future launches.

### Windows

Download and extract the Windows ZIP to a stable folder, then launch Skunkworks
from the extracted application. Version 1.0 is unsigned, so Windows may display
a publisher warning. Preserve the whole extracted application directory.

### Linux

Download and extract the Linux ZIP, mark the bundled Skunkworks executable as
executable if necessary, and run it from the extracted directory. AppImage or
Flatpak packaging can be added in a later release.

## Run directly from GitHub source

Source users need Git and Python 3.14. A Git clone is recommended because it
makes upgrades and version selection explicit:

```bash
git clone https://github.com/Ziegenbagel/skunkworks.git
cd skunkworks
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m src.ui.app
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. Users who
do not want Git may download the **Source code** archive from a specific GitHub
release, extract it, and run the same environment/install commands from the
extracted directory.

Developers using `uv` can reproduce the locked environment:

```bash
uv sync --locked
uv run python -m src.ui.app
```

Do not run unreviewed source from a moving branch against a valuable game
account. Prefer a signed release tag, and review configuration before enabling
automatic orders.

## Updating a source checkout

Stop Skunkworks, create a verified database backup, then update to a named tag:

```bash
python -m tools.database_maintenance --backup /safe/path/skunkworks.sqlite3
git fetch --tags
git checkout v1.0.1
python -m pip install -e .
python -m src.ui.app
```

Never commit `.env`, databases, backups, runtime snapshots, or diagnostic logs.

## User-data locations

Skunkworks keeps mutable state outside the installed application:

| Platform | Database/configuration | Cache/snapshots | Logs |
|---|---|---|---|
| macOS | `~/Library/Application Support/Skunkworks` | `~/Library/Caches/Skunkworks` | `~/Library/Logs/Skunkworks` |
| Windows | `%LOCALAPPDATA%\Skunkworks\Data` and `Config` | `%LOCALAPPDATA%\Skunkworks\Cache` | `%LOCALAPPDATA%\Skunkworks\Logs` |
| Linux | `$XDG_DATA_HOME/skunkworks` and `$XDG_CONFIG_HOME/skunkworks` | `$XDG_CACHE_HOME/skunkworks` | `$XDG_STATE_HOME/skunkworks` |

When XDG variables are unset, Linux uses their conventional paths under
`~/.local/share`, `~/.config`, `~/.cache`, and `~/.local/state`. Developers may
set `SKUNKWORKS_HOME` to isolate all writable state under one private directory.

On first launch after upgrading from a source-tree installation, Skunkworks
copies the legacy SQLite database through SQLite's online backup API and verifies
it before use. The original is preserved. Existing destination data is never
overwritten automatically.
