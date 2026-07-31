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
            CommandType.MOVE_PROBE: self._move_probe,
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

    def _move_probe(self, command):
        return self.capabilities.probes.move(
            command.probe_id,
            command.payload["target"],
        )
