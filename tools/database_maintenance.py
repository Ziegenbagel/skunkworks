"""Inspect, back up, and compact a Skunkworks database safely."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.data import DataEngine


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--backup", metavar="PATH")
    actions.add_argument("--compact", action="store_true")
    actions.add_argument(
        "--vacuum",
        action="store_true",
        help="Compact and reclaim disk space; run only while Skunkworks is stopped.",
    )
    parser.add_argument("--retain-days", type=int, default=30)
    return parser


def main(argv=None):
    arguments = build_parser().parse_args(argv)
    engine = DataEngine(Path(arguments.database) if arguments.database else None)
    before = engine.database_report()
    result = None
    if arguments.backup:
        result = engine.backup(arguments.backup)
    elif arguments.compact or arguments.vacuum:
        result = engine.compact_history(
            arguments.retain_days,
            vacuum=arguments.vacuum,
        )
    payload = {
        "integrity": engine.integrity_report(),
        "before": before,
        "action": result,
        "after": engine.database_report(),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["integrity"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
