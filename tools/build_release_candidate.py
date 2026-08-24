"""Build a bounded unsigned standalone release candidate with PyInstaller.

Only explicitly listed application data enters the package. Private runtime
state and developer directories cannot become package inputs merely because
they exist beside the source tree.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build" / "release-candidate"


def command(output_directory: Path, build_directory: Path | None = None) -> list[str]:
    build_directory = build_directory or output_directory.parent / ".release-build"
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name=Skunkworks",
        f"--distpath={output_directory}",
        f"--workpath={build_directory / 'work'}",
        f"--specpath={build_directory / 'spec'}",
        "--hidden-import=PySide6.QtMultimedia",
        f"--add-data={ROOT / 'src/ui/qml'}{os.pathsep}src/ui/qml",
        f"--add-data={ROOT / 'src/ui/assets'}{os.pathsep}src/ui/assets",
        f"--add-data={ROOT / 'config'}{os.pathsep}config",
        f"--add-data={ROOT / 'docs/user-guide/Skunkworks_Operator_Manual.docx'}{os.pathsep}docs/user-guide",
        f"--add-data={ROOT / 'docs/user-guide/CHANGELOG.md'}{os.pathsep}docs/user-guide",
        f"--add-data={ROOT / 'LICENSE'}{os.pathsep}.",
        f"--add-data={ROOT / 'NOTICE'}{os.pathsep}.",
        str(ROOT / "skunkworks_app.py"),
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args(argv)
    output = options.output_dir.resolve()
    temporary_root = Path(tempfile.gettempdir()).resolve()
    in_repository = ROOT in output.parents
    in_temporary_root = temporary_root == output or temporary_root in output.parents
    if output == ROOT or not (in_repository or in_temporary_root):
        parser.error(
            "Output directory must be under the repository or system temporary directory."
        )
    if options.clean and output.exists():
        shutil.rmtree(output)
    build_directory = output.parent / f".{output.name}-build"
    if options.clean and build_directory.exists():
        shutil.rmtree(build_directory)
    output.mkdir(parents=True, exist_ok=True)
    args = command(output, build_directory)
    if options.dry_run:
        print(" ".join(str(item) for item in args))
        return 0
    build_directory.mkdir(parents=True, exist_ok=True)
    print(
        f"Building unsigned {platform.system()} {platform.machine()} candidate in {output}"
    )
    environment = os.environ.copy()
    environment.setdefault("COPYFILE_DISABLE", "1")
    environment.setdefault("PYINSTALLER_CONFIG_DIR", str(build_directory / "cache"))
    subprocess.run(args, cwd=ROOT, env=environment, check=True)
    if sys.platform == "darwin":
        collection_directory = output / "Skunkworks"
        if collection_directory.exists():
            shutil.rmtree(collection_directory)
    shutil.rmtree(build_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
