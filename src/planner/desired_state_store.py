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

    def load(self):
        stored = self.data_engine.get_preference(
            self.PREFERENCE_KEY
        )

        if stored is not None:
            return DesiredState.from_dict(
                json.loads(stored)
            )

        if not self.default_path.exists():
            return DesiredState.empty()

        with self.default_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return DesiredState.from_dict(
                json.load(file)
            )

    def save(self, desired_state):
        self.data_engine.set_preference(
            self.PREFERENCE_KEY,
            json.dumps(
                desired_state.to_dict(),
                sort_keys=True,
            ),
        )
