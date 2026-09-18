"""Last-mile validation for proposed commands."""

from dataclasses import replace

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
            CommandType.MANNY_TRANSFER_DEUTERIUM,
            CommandType.MANNY_REFILL_DEUTERIUM_TANK,
            CommandType.MANNY_ASSEMBLE_PROBE,
            CommandType.MANNY_REPAIR,
            CommandType.MANNY_INSPECT_SECTOR_OBJECT,
            CommandType.MANNY_RECOVER_STORAGE_CONTAINER,
            CommandType.MANNY_DETACH_STORAGE_CONTAINER,
            CommandType.MOVE_PROBE,
        } and probe["status"] not in {"idle", "arrived"}:
            blockers.append("probe_unavailable")

        if command.type == CommandType.MOVE_PROBE:
            blockers.extend(
                self._move_blockers(command)
            )
        if command.type == CommandType.CANCEL_PROBE_MOVE:
            blockers.extend(self._cancel_move_blockers())

        if command.type in {
            CommandType.MANNY_CRAFT,
            CommandType.MANNY_MINE,
            CommandType.MANNY_TRANSFER_DEUTERIUM,
            CommandType.MANNY_REFILL_DEUTERIUM_TANK,
            CommandType.MANNY_ASSEMBLE_PROBE,
            CommandType.MANNY_REPAIR,
            CommandType.MANNY_INSPECT_SECTOR_OBJECT,
            CommandType.MANNY_RECOVER_STORAGE_CONTAINER,
            CommandType.MANNY_DETACH_STORAGE_CONTAINER,
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

        if command.metadata.get("transportTransfer") and any(
            "transfer" in task_type
            and "deuterium" in task_type
            and "probe" in task_type
            for manny in self.operations.world.mannies.get("mannies", [])
            if (
                task_type := str(
                    self.operations.mannies._task_type(manny) or ""
                ).lower().replace("-", "_").replace(" ", "_")
            )
        ):
            blockers.append("transport_transfer_already_active")

        if command.type == CommandType.MANNY_RECOVER_STORAGE_CONTAINER:
            object_ids = {
                str(item.get("id", item.get("containerId")))
                for item in self.operations.containers.detached()
            }
            if str(command.payload.get("objectId")) not in object_ids:
                blockers.append("transport_container_not_available")
            if (
                self.operations.travel_safety.additional_container_count()
                >= max(
                    0,
                    self.operations.travel_safety.container_break_threshold() - 1,
                )
            ):
                blockers.append("safe_container_limit_reached")

        if command.type == CommandType.MANNY_DETACH_STORAGE_CONTAINER:
            container_ids = {
                str(item.get("id", item.get("containerId")))
                for item in self.operations.containers.attached()
            }
            if str(command.payload.get("containerId")) not in container_ids:
                blockers.append("transport_container_not_attached")

        if command.type in {
            CommandType.MANNY_RECOVER_STORAGE_CONTAINER,
            CommandType.MANNY_DETACH_STORAGE_CONTAINER,
        }:
            expected = command.metadata.get("expectedSector")
            current = self.operations.travel.current_sector()
            if isinstance(expected, dict):
                from src.models.galaxy import SectorCoordinates
                try:
                    expected = SectorCoordinates.from_api(expected)
                except (KeyError, TypeError, ValueError):
                    expected = None
            if expected is not None and current != expected:
                blockers.append("transport_wrong_sector")

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
        warnings = (
            assessment.hazards
            if assessment is not None
            else ()
        )
        trigger = self._automatic_repair_threshold(command, "Trigger")
        if trigger > 0 and self._live_integrity() > trigger:
            warnings = tuple(
                replace(warning, acknowledgement_recommended=False)
                if warning.code == "arrival_integrity_low"
                else warning
                for warning in warnings
            )
        return warnings

    def _move_blockers(self, command):
        target = command.payload.get("target")

        if not isinstance(target, dict):
            return ("invalid_target",)

        try:
            from src.models.galaxy import SectorCoordinates

            coordinates = SectorCoordinates.from_api(target)
        except (KeyError, TypeError, ValueError):
            return ("invalid_target",)

        blockers = list(
            blocker
            for blocker in self.operations.travel.travel_blockers(
                coordinates
            )
            if blocker != "already_at_destination"
        )
        if command.metadata.get("workflowAuthorized", False):
            blockers.extend(
                self.operations.travel.automatic_manny_departure_blockers(coordinates)
            )
            trigger = self._automatic_repair_threshold(command, "Trigger")
            target = self._automatic_repair_threshold(command, "Target")
            integrity = self._live_integrity()
            repair_active = any(
                self.operations.mannies._task_type(manny) in {"repair", "repairing"}
                for manny in self.operations.mannies.all()
            )
            if trigger > 0 and integrity < target and (
                integrity <= trigger or repair_active
            ):
                blockers.append("repair_required_before_travel")
        if command.metadata.get("requireScutCoverage"):
            origin = self.operations.travel.current_sector()
            if origin is not None and (
                self.operations.travel_safety.scut_route_covered(
                    origin,
                    (coordinates,),
                ) is False
            ):
                blockers.append("route_leaves_scut_coverage")
        return tuple(dict.fromkeys(blockers))

    def _automatic_repair_threshold(self, command, boundary):
        try:
            return float(
                command.metadata.get(
                    f"automaticRepair{boundary}Percent",
                    0,
                ) or 0
            )
        except (TypeError, ValueError):
            return 0.0

    def _live_integrity(self):
        try:
            return float(
                (self.operations.world.probe.get("systems") or {}).get(
                    "integrityPercent",
                    100,
                )
            )
        except (TypeError, ValueError):
            return 0.0

    def _cancel_move_blockers(self):
        movement = self.operations.world.probe.get("movement") or {}
        phase = str(
            movement.get("phase") or movement.get("status") or ""
        ).casefold()
        blockers = []
        if phase != "preparing":
            blockers.append("movement_not_cancellable")
        target = self.operations.travel.active_movement_target()
        if not self.operations.travel.automatic_manny_departure_blockers(target):
            blockers.append("all_mannies_aboard")
        return tuple(blockers)
