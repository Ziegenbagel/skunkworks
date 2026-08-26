"""Stable console bootstrap for source, editable, and frozen installations."""

from __future__ import annotations

import sys
from pathlib import Path


def run():
    """Launch Mission Control with the installed project root importable.

    Setuptools' Python 3.14 editable finder can expose the top-level ``src``
    package without resolving its ``src.ui`` child from a generated console
    script. Adding the directory containing this installed bootstrap lets the
    standard path finder handle both editable checkouts and ordinary wheels.
    """

    package_root = str(Path(__file__).resolve().parent)
    if package_root not in sys.path:
        sys.path.insert(0, package_root)
    from src.ui.app import run as run_application

    return run_application()


if __name__ == "__main__":
    raise SystemExit(run())
