"""Load and persist declarative planning goals."""

import json
from pathlib import Path

from src.planner.desired_state import DesiredState


class DesiredStateStore:
    PREFERENCE_KEY = "desired_state"

    def __init__(
        self,
        data_engine,
        default_path="config/desired_state.json",
    ):
        self.data_engine = data_engine
        self.default_path = Path(default_path)

    def load(self, probe_id=None):
        stored = self.data_engine.get_preference(
            self.PREFERENCE_KEY
        )

        if stored is not None:
            value = json.loads(stored)
            if value.get("_scopeVersion") == 1:
                scoped = value.get("probes", {}).get(str(probe_id))
                value = scoped if scoped is not None else value.get("default", {})
            return DesiredState.from_dict(value)

        if not self.default_path.exists():
            return DesiredState.empty()

        with self.default_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return DesiredState.from_dict(
                json.load(file)
            )

    def save(self, desired_state, probe_id=None):
        if probe_id is None:
            value = desired_state.to_dict()
        else:
            stored = self.data_engine.get_preference(self.PREFERENCE_KEY)
            current = json.loads(stored) if stored is not None else {}
            if current.get("_scopeVersion") != 1:
                current = {
                    "_scopeVersion": 1,
                    "default": current,
                    "probes": {},
                }
            current.setdefault("probes", {})[str(probe_id)] = desired_state.to_dict()
            value = current
        self.data_engine.set_preference(
            self.PREFERENCE_KEY,
            json.dumps(
                value,
                sort_keys=True,
            ),
        )
