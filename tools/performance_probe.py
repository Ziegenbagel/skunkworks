"""Measure bounded local database operations without contacting the game API."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from src.data import DataEngine


def timed(operation, repetitions):
    samples = []
    for _ in range(repetitions):
        started = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "minimumMs": min(samples),
        "medianMs": statistics.median(samples),
        "maximumMs": max(samples),
        "samples": repetitions,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database")
    parser.add_argument("--repetitions", type=int, default=5)
    arguments = parser.parse_args(argv)
    repetitions = max(1, arguments.repetitions)
    database = Path(arguments.database) if arguments.database else None
    engine = DataEngine(database)
    results = {
        "database": str(engine.path),
        "databaseHealth": engine.database_report(),
        "integrity": timed(engine.integrity_report, repetitions),
        "databaseReport": timed(engine.database_report, repetitions),
        "galaxyRebuild": timed(
            lambda: engine.galaxy_map(max_age_seconds=0), repetitions,
        ),
    }
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
