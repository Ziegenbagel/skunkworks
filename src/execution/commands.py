"""Typed, deterministic descriptions of possible game mutations."""

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum


class CommandType(StrEnum):
    MANNY_CRAFT = "manny_craft"
    ATOMIC_PRINTER_CRAFT = "atomic_printer_craft"
    MANNY_MINE = "manny_mine"
    MANNY_ASSEMBLE_PROBE = "manny_assemble_probe"
    MANNY_REPAIR = "manny_repair"
    MOVE_PROBE = "move_probe"


@dataclass(frozen=True)
class Command:
    """A proposed mutation that has not been sent to the API."""

    type: CommandType
    probe_id: int
    payload: dict
    reason: str
    priority: int
    target_id: str | int | None = None
    source_action: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def fingerprint(self):
        canonical = json.dumps(
            {
                "type": self.type.value,
                "probeId": self.probe_id,
                "targetId": self.target_id,
                "payload": self.payload,
                "metadata": self.metadata,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(
            canonical.encode("utf-8")
        ).hexdigest()

    def to_dict(self):
        return {
            "type": self.type.value,
            "probeId": self.probe_id,
            "targetId": self.target_id,
            "payload": self.payload,
            "reason": self.reason,
            "priority": self.priority,
            "sourceAction": self.source_action,
            "metadata": self.metadata,
            "fingerprint": self.fingerprint,
        }
