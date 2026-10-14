"""Allowlisted mapping from typed commands to mutation gateways."""

from .commands import CommandType


class CapabilityDispatcher:
    def __init__(self, capabilities):
        self.capabilities = capabilities

    def dispatch(self, command):
        handlers = {
            CommandType.MANNY_CRAFT: self._manny_craft,
            CommandType.ATOMIC_PRINTER_CRAFT: self._printer_craft,
            CommandType.MANNY_MINE: self._manny_mine,
            CommandType.MANNY_TRANSFER_PROBE: lambda command: self.capabilities.mannies.start_task(command.probe_id, command.target_id, "transfer-to-probe", command.payload),
            CommandType.MANNY_TRANSFER_DEUTERIUM: self._manny_transfer_deuterium,
            CommandType.MANNY_REFILL_DEUTERIUM_TANK: self._manny_refill_deuterium_tank,
            CommandType.MANNY_ASSEMBLE_PROBE: self._manny_assemble_probe,
            CommandType.MANNY_UPGRADE: self._manny_upgrade,
            CommandType.MANNY_REPAIR: self._manny_repair,
            CommandType.MANNY_INSPECT_SECTOR_OBJECT: self._manny_inspect_sector_object,
            CommandType.MANNY_RECOVER_STORAGE_CONTAINER: self._manny_recover_storage_container,
            CommandType.MANNY_DETACH_STORAGE_CONTAINER: self._manny_detach_storage_container,
            CommandType.DEPLOY_SCUT_RELAY: self._deploy_relay,
            CommandType.MANNY_ACTIVATE_RELAY: self._activate_relay,
            CommandType.MANNY_INSTALL_BEACON: self._install_beacon,
            CommandType.MANNY_LOAD_HUB_OUTPUT: self._load_hub_output,
            CommandType.MOVE_PROBE: self._move_probe,
            CommandType.CANCEL_PROBE_MOVE: self._cancel_probe_move,
        }
        try:
            handler = handlers[command.type]
        except KeyError as error:
            raise ValueError(
                f"Unsupported command type: {command.type}"
            ) from error
        return handler(command)

    def _manny_craft(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id,
            command.target_id,
            "craft",
            command.payload,
        )

    def _printer_craft(self, command):
        return self.capabilities.mannies.atomic_printer_craft(
            command.probe_id,
            command.payload["recipe"],
        )

    def _manny_mine(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id,
            command.target_id,
            "mine",
            command.payload,
        )

    def _manny_transfer_deuterium(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id,
            command.target_id,
            "transfer-deuterium-to-probe",
            command.payload,
        )

    def _manny_refill_deuterium_tank(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id,
            command.target_id,
            "refill-deuterium-tank",
            {},
        )

    def _manny_assemble_probe(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id,
            command.target_id,
            "assemble-probe",
            command.payload,
        )

    def _manny_upgrade(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id, command.target_id, "improve-probe", command.payload,
        )

    def _manny_repair(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id, command.target_id, "repair", command.payload,
        )

    def _manny_inspect_sector_object(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id,
            command.target_id,
            "inspect-sector-object",
            command.payload,
        )

    def _manny_recover_storage_container(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id, command.target_id,
            "recover-storage-container", command.payload,
        )

    def _manny_detach_storage_container(self, command):
        return self.capabilities.mannies.start_task(
            command.probe_id, command.target_id,
            "detach-storage-container", command.payload,
        )

    def _move_probe(self, command):
        return self.capabilities.probes.move(
            command.probe_id,
            command.payload["target"],
        )

    def _cancel_probe_move(self, command):
        return self.capabilities.probes.cancel_move(command.probe_id)

    def _deploy_relay(self, command):
        return self.capabilities.storage.jettison(command.probe_id, command.payload["itemId"])

    def _activate_relay(self, command):
        return self.capabilities.mannies.start_task(command.probe_id, command.target_id,
                                                   "turn-on-relay", command.payload)

    def _install_beacon(self, command):
        return self.capabilities.mannies.start_task(command.probe_id, command.target_id,
                                                   "install-scut-transit-beacon", command.payload)

    def _load_hub_output(self, command):
        return self.capabilities.storage.move(command.probe_id, {**command.payload, "actorMannyId": command.target_id})
