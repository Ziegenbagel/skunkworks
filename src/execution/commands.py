"""Typed, deterministic descriptions of possible game mutations."""

import hashlib
import json
from dataclasses import dataclass, field
from enum import StrEnum


class CommandType(StrEnum):
    MANNY_CRAFT = "manny_craft"
    ATOMIC_PRINTER_CRAFT = "atomic_printer_craft"
    MANNY_MINE = "manny_mine"
    MANNY_TRANSFER_PROBE = "manny_transfer_probe"
    MANNY_TRANSFER_DEUTERIUM = "manny_transfer_deuterium"
    MANNY_REFILL_DEUTERIUM_TANK = "manny_refill_deuterium_tank"
    MANNY_ASSEMBLE_PROBE = "manny_assemble_probe"
    MANNY_UPGRADE = "manny_upgrade"
    MANNY_REPAIR = "manny_repair"
    MANNY_INSPECT_SECTOR_OBJECT = "manny_inspect_sector_object"
    MANNY_RECOVER_STORAGE_CONTAINER = "manny_recover_storage_container"
    MANNY_DETACH_STORAGE_CONTAINER = "manny_detach_storage_container"
    DEPLOY_SCUT_RELAY = "deploy_scut_relay"
    MANNY_ACTIVATE_RELAY = "manny_activate_relay"
    MANNY_INSTALL_BEACON = "manny_install_beacon"
    MANNY_LOAD_HUB_OUTPUT = "manny_load_hub_output"
    MOVE_PROBE = "move_probe"
    CANCEL_PROBE_MOVE = "cancel_probe_move"


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
        if self.type == CommandType.MANNY_UPGRADE:
            # A selected installation is one operation across workers/restarts.
            return hashlib.sha256(json.dumps({
                "type": self.type.value, "probeId": self.probe_id,
                "payload": self.payload, "scope": self.metadata.get("upgradeScope"),
            }, sort_keys=True).encode("utf-8")).hexdigest()
        identity_metadata = dict(self.metadata)
        target_id = self.target_id
        if self.type in {
            CommandType.MANNY_ACTIVATE_RELAY,
            CommandType.MANNY_INSTALL_BEACON,
            CommandType.MANNY_LOAD_HUB_OUTPUT,
            CommandType.MANNY_INSPECT_SECTOR_OBJECT,
            CommandType.MANNY_RECOVER_STORAGE_CONTAINER,
            CommandType.MANNY_DETACH_STORAGE_CONTAINER,
        }:
            # Inspection is a one-time mutation of the sector object, not of
            # the selected worker. A refresh may choose another idle Manny;
            # that must remain the same command identity so leases and the
            # completed-action journal prevent duplicate inspections.
            target_id = None
            for key in (
                "mannyName", "objectName", "objectType", "containerName",
                "workflowAuthorized",
            ):
                identity_metadata.pop(key, None)
        # Route-level consent changes execution authorization, not the game
        # mutation itself. Keeping it out of the identity lets the exact hop
        # acknowledged by the operator remain selectable after consent is
        # persisted on the durable route goal.
        for key in ("assignedMannyId", "campaignCrew", "excludedMannyIds"):
            identity_metadata.pop(key, None)
        identity_metadata.pop("routeRiskAcknowledged", None)
        canonical = json.dumps(
            {
                "type": self.type.value,
                "probeId": self.probe_id,
                "targetId": target_id,
                "payload": self.payload,
                "metadata": identity_metadata,
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
