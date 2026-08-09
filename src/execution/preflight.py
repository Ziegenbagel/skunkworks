"""Last-mile validation for proposed commands."""

from .commands import CommandType


class PreflightValidator:
    def __init__(self, operations, probe_id):
        self.operations = operations
        self.probe_id = probe_id

    def blockers(self, command):
        blockers = []
        probe = self.operations.probes.current()

        if command.probe_id != self.probe_id:
            blockers.append("wrong_probe_context")

        if command.probe_id != probe["id"]:
            blockers.append("world_probe_mismatch")

        if not probe["telemetry_available"]:
            blockers.append("telemetry_unavailable")

        if command.type in {
            CommandType.MANNY_CRAFT,
            CommandType.ATOMIC_PRINTER_CRAFT,
            CommandType.MANNY_MINE,
            CommandType.MANNY_ASSEMBLE_PROBE,
            CommandType.MANNY_REPAIR,
            CommandType.MOVE_PROBE,
        } and probe["status"] != "idle":
            blockers.append("probe_unavailable")

        if command.type == CommandType.MOVE_PROBE:
            blockers.extend(
                self._move_blockers(command)
            )

        if command.type in {
            CommandType.MANNY_CRAFT,
            CommandType.MANNY_MINE,
            CommandType.MANNY_ASSEMBLE_PROBE,
            CommandType.MANNY_REPAIR,
        }:
            manny = next(
                (
                    candidate
                    for candidate in self.operations.world.mannies.get(
                        "mannies",
                        [],
                    )
                    if candidate["id"] == command.target_id
                ),
                None,
            )
            if manny is None:
                blockers.append("manny_not_found")
            elif (
                manny.get("currentTask") is not None
                or not manny.get("canReceiveOrders", False)
            ):
                blockers.append("manny_unavailable")

        return tuple(dict.fromkeys(blockers))

    def warnings(self, command):
        if command.type != CommandType.MOVE_PROBE:
            return ()

        target = command.payload.get("target")

        try:
            from src.models.galaxy import SectorCoordinates

            coordinates = SectorCoordinates.from_api(target)
        except (KeyError, TypeError, ValueError):
            return ()

        assessment = self.operations.travel_safety.assess(
            coordinates
        )
        return (
            assessment.hazards
            if assessment is not None
            else ()
        )

    def _move_blockers(self, command):
        target = command.payload.get("target")

        if not isinstance(target, dict):
            return ("invalid_target",)

        try:
            from src.models.galaxy import SectorCoordinates

            coordinates = SectorCoordinates.from_api(target)
        except (KeyError, TypeError, ValueError):
            return ("invalid_target",)

        return tuple(
            blocker
            for blocker in self.operations.travel.travel_blockers(
                coordinates
            )
            if blocker != "already_at_destination"
        )
