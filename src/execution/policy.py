"""Player-owned policy for command preparation and future execution."""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from src.application.paths import application_paths

from .commands import CommandType


class ExecutionMode(StrEnum):
    OBSERVE = "observe"
    APPROVE = "approve"
    AUTOMATIC = "automatic"


@dataclass(frozen=True)
class ExecutionPolicy:
    mode: ExecutionMode = ExecutionMode.OBSERVE
    live_execution_enabled: bool = False
    allowed_command_types: frozenset[CommandType] = field(
        default_factory=frozenset
    )
    max_commands_per_cycle: int = 1

    def __post_init__(self):
        if self.max_commands_per_cycle < 1:
            raise ValueError(
                "maxCommandsPerCycle must be at least one."
            )

    @classmethod
    def from_dict(cls, value):
        return cls(
            mode=ExecutionMode(value.get("mode", "observe")),
            live_execution_enabled=bool(
                value.get("liveExecutionEnabled", False)
            ),
            allowed_command_types=frozenset(
                CommandType(command_type)
                for command_type in value.get(
                    "allowedCommandTypes",
                    [],
                )
            ),
            max_commands_per_cycle=int(
                value.get("maxCommandsPerCycle", 1)
            ),
        )

    def to_dict(self):
        return {
            "mode": self.mode.value,
            "liveExecutionEnabled": self.live_execution_enabled,
            "allowedCommandTypes": sorted(
                item.value for item in self.allowed_command_types
            ),
            "maxCommandsPerCycle": self.max_commands_per_cycle,
        }


class ExecutionPolicyStore:
    def __init__(
        self,
        path=None,
    ):
        self.path = Path(path) if path is not None else application_paths().config_file(
            "execution_policy.json"
        )

    def _read(self):
        if not self.path.exists():
            return None

        with self.path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def load(self, probe_id=None):
        value = self._read()
        if value is None:
            return ExecutionPolicy()
        if "probes" not in value:
            return ExecutionPolicy.from_dict(value)
        if probe_id is not None:
            scoped = value.get("probes", {}).get(str(probe_id))
            if scoped is not None:
                return ExecutionPolicy.from_dict(scoped)
        return ExecutionPolicy.from_dict(value.get("default", {}))

    def save(self, policy, probe_id=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if probe_id is None:
            value = policy.to_dict()
        else:
            current = self._read() or {}
            if "probes" in current:
                value = current
            else:
                value = {
                    "default": current,
                    "probes": {},
                }
            value.setdefault("probes", {})[str(probe_id)] = policy.to_dict()
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(value, file, indent=2)
            file.write("\n")
