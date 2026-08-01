"""Player-owned policy for command preparation and future execution."""

import json
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

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


class ExecutionPolicyStore:
    def __init__(
        self,
        path="config/execution_policy.json",
    ):
        self.path = Path(path)

    def load(self):
        if not self.path.exists():
            return ExecutionPolicy()

        with self.path.open("r", encoding="utf-8") as file:
            return ExecutionPolicy.from_dict(json.load(file))

    def save(self, policy):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump({
                "mode": policy.mode.value,
                "liveExecutionEnabled": policy.live_execution_enabled,
                "allowedCommandTypes": sorted(item.value for item in policy.allowed_command_types),
                "maxCommandsPerCycle": policy.max_commands_per_cycle,
            }, file, indent=2)
            file.write("\n")
