"""Qt bridge and live read-only data loader for Mission Control."""

from __future__ import annotations

import traceback
import json
import re
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import requests
from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from src.api.capabilities import GameCapabilities
from src.api.client import GameClient
from src.api.contract import MAXIMUM_API_VERSION, MINIMUM_API_VERSION
from src.application.hazard_context import HazardContextLoader
from src.application.history_sync import HistorySynchronizer
from src.application.probe_selector import ProbeSelector
from src.data import DataEngine
from src.intelligence.world_builder import WorldBuilder
from src.operations.operations import Operations
from src.operations.logistics import FleetRoleService
from src.operations import OperationFactory, OperationStore, RoundTripTransportPlan
from src.presentation import MissionControlViewModelBuilder
from src.recipes.manager import RecipeManager
from src.safety.policy import TravelSafetyPolicyStore
from src.safety.resources import ResourceSafetyPolicyStore
from src.planner.desired_state import DesiredState, FuelGoal, TravelGoal
from src.planner.desired_state_store import DesiredStateStore
from src.models.galaxy import SectorCoordinates
from src.snapshot.manager import SnapshotManager
from src.security import CredentialStore
from src.planner.planner import Planner
from src.planner.task import Task
from src.planner.assembly import PROBE_ASSEMBLY_REQUIREMENTS
from src.execution import (
    AutomationRuntime, CapabilityDispatcher, CommandPreparer,
    CommandType, ExecutionMode, ExecutionPolicy,
)
from src.execution.policy import ExecutionPolicyStore
from src.diagnostics import diagnostic_log_directory, log_handled_error
from src.reporting import DailyProbeReportService


class MissionControlDataService:
    """Build one authoritative dashboard snapshot for a selected probe."""

    def __init__(
        self,
        client=None,
        data_engine=None,
        snapshot_manager=None,
        world_builder=None,
        recipes=None,
    ):
        self.client = client or GameClient()
        self.data_engine = data_engine or DataEngine()
        self.snapshot_manager = snapshot_manager or SnapshotManager(self.client)
        self.world_builder = world_builder or WorldBuilder()
        self.recipes = recipes or RecipeManager()
        self.capabilities = GameCapabilities(self.client)
        self.probe_selector = ProbeSelector()
        self._initialized = False
        self.api_version = None
        self._operations = None
        self._selected_probe_id = None
        self._last_scan_result = None
        self._prepared_commands = ()
        self._logbook_page_probes = {}
        self._history_sync_at = {}
        self._hazard_cache = {}
        self._logbook_cache = {}

    def load(self, probe_id=None, include_archival=True, progress=None):
        report = progress or (lambda percent, label: None)
        report(5, "Checking API compatibility and recipes")
        self._initialize()
        report(15, "Loading commander and fleet")
        player = self.client.get_player()
        probe_data = self.client.get_probes()
        selected = self.probe_selector.select(
            probe_data,
            arguments=[],
            preferred_probe_id=probe_id or self.data_engine.remembered_probe_id(),
        )
        self.data_engine.remember_probe(selected["id"])

        report(30, "Loading focused probe telemetry")
        details = self.client.get_probe(selected["id"])
        probe = details.get("probe", details)
        mannies = None
        if selected.get("isReachable", True):
            report(42, "Loading Manny tasks")
            mannies = self.client.get_mannies(selected["id"])

        report(52, "Loading sector and inventory")
        world = self._build_world(player, probe_data, probe, selected, mannies)
        selected_id = int(selected["id"])
        now = time.monotonic()
        # Secondary-probe interaction and fleet automation need current probe
        # telemetry, not a repeated account-wide archival import.  The default
        # probe performs that slower synchronization at most once per five
        # minutes; every load still records the live world snapshot locally.
        should_sync_history = (
            include_archival
            and bool(selected.get("isDefault"))
            and now - self._history_sync_at.get(selected_id, 0) >= 300
        )
        if should_sync_history:
            report(62, "Synchronizing fleet history")
            sync_failures = HistorySynchronizer(
                self.data_engine,
                self.capabilities,
            ).sync(
                world,
                selected_id,
                reachable=selected.get("isReachable", True),
            )
            self._history_sync_at[selected_id] = now
        else:
            self.data_engine.record_world(world)
            sync_failures = {}
        world.galaxy = self.data_engine.galaxy_map()
        report(76, "Evaluating hazards and automation")
        cached_hazards = self._hazard_cache.get(selected_id)
        if cached_hazards and now - cached_hazards[0] < 60:
            world.hazard_context = cached_hazards[1]
        else:
            world.hazard_context = HazardContextLoader(self.capabilities).load(
                world,
                selected_id,
                reachable=selected.get("isReachable", True),
            )
            self._hazard_cache[selected_id] = (now, world.hazard_context)

        operations = Operations(
            world,
            self.recipes,
            TravelSafetyPolicyStore().load(),
            self.data_engine,
            ResourceSafetyPolicyStore().load(),
            self.capabilities,
        )
        self._operations = operations
        self._selected_probe_id = selected["id"]
        explorer_scan = self._auto_scan_explorer_arrival(selected["id"], operations)
        if explorer_scan is not None:
            self._last_scan_result = explorer_scan
            world.galaxy = self.data_engine.galaxy_map()
        dashboard = MissionControlViewModelBuilder(
            operations,
            self.data_engine,
        ).build()
        report(92, "Preparing mission-control displays")
        dashboard["apiVersion"] = self.api_version
        dashboard["player"] = self._player_view(player)
        options = [self._probe_option(item) for item in probe_data.get("probes", ())]
        for option in options:
            if option["id"] == selected["id"]:
                option["sectorLabel"] = dashboard["focus"]["sectorLabel"]
                option["status"] = dashboard["focus"]["status"]
                option["model"] = dashboard["focus"]["model"]
        dashboard["probeOptions"] = options
        default_probe = next(
            (item for item in options if item.get("isDefault")),
            None,
        )
        dashboard["defaultProbeId"] = (
            default_probe["id"] if default_probe is not None else None
        )
        dashboard["syncFailures"] = sync_failures
        dashboard["emergencyStopActive"] = self.data_engine.emergency_stop_active()
        if self._last_scan_result is not None:
            dashboard.setdefault("navigation", {})["scanResult"] = self._last_scan_result
        desired_state = DesiredStateStore(self.data_engine).load(selected["id"])
        automation = desired_state.to_dict()
        probes = world.fleet.get("probes", ()) if getattr(world, "fleet", None) else (probe,)
        model_counts = {}
        for fleet_probe in probes:
            model = fleet_probe.get("model", "generic")
            model_counts[model] = model_counts.get(model, 0) + 1
        automation["fleetStatus"] = [
            {
                "model": goal.model,
                "current": model_counts.get(goal.model, 0),
                "target": goal.quantity,
                "shortage": max(0, goal.quantity - model_counts.get(goal.model, 0)),
                "priority": goal.priority,
            }
            for goal in desired_state.fleet
        ]
        automation["probeRoles"] = {
            str(row["asset_id"]): row["role"]
            for row in FleetRoleService(self.data_engine).all("probe")
        }
        reserve_sources = FleetRoleService(self.data_engine).deuterium_sources(probes)
        automation["deuteriumSources"] = reserve_sources
        automation["availableReserveDeuterium"] = sum(
            source["availableAmount"] for source in reserve_sources if source["fresh"]
        )
        dashboard["deuteriumSupply"] = {
            "sources": reserve_sources,
            "availableAmount": automation["availableReserveDeuterium"],
        }
        automation["transportCycles"] = [
            json.loads(row["payload_json"])
            for row in self.data_engine.operation_records()
            if json.loads(row["payload_json"]).get("metadata", {}).get("template") == "round_trip_transport"
        ]
        try:
            automation["namingPolicy"] = json.loads(
                self.data_engine.get_preference("fleet_naming_policy", "{}")
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            automation["namingPolicy"] = {}
        dashboard["automation"] = automation
        dashboard["automationRuntime"] = self.automation_view(operations, selected["id"])
        dashboard["crafting"] = {
            "recipes": tuple({
                "id": recipe.get("id"),
                "name": recipe.get("name") or str(recipe.get("id", "")).replace("_", " ").title(),
                "description": recipe.get("description", ""),
                "craftableBy": tuple(recipe.get("craftableBy", ())),
                "durationSeconds": int(recipe.get("durationSeconds", 0) or 0),
                "ingredients": tuple(recipe.get("ingredients", ())),
            } for recipe in sorted(
                self.recipes.all(),
                key=lambda item: str(item.get("name") or item.get("id") or "").lower(),
            )),
            "probeAssemblies": tuple({
                "model": model,
                "name": (
                    "Generic Class Probe"
                    if model == "generic"
                    else "Tanker Class Probe"
                    if model == "deuterium_tanker"
                    else model.replace("_", " ").title()
                ),
                "components": tuple({
                    "type": component,
                    "name": (
                        (self.recipes.get(component) or {}).get("name")
                        or component.replace("_", " ").title()
                    ),
                    "quantity": quantity,
                } for component, quantity in components),
                "assemblyAvailable": bool(components),
            } for model, components in PROBE_ASSEMBLY_REQUIREMENTS.items()),
            "idleMannies": dashboard.get("inventoryManagement", {}).get("idleMannies", ()),
        }
        improvements_response = world.hazard_context.get("improvements") or {}
        dashboard["probeImprovements"] = tuple({
            "id": improvement.get("id"),
            "displayName": improvement.get("name") or str(improvement.get("id", "")).replace("_", " ").title(),
            "description": improvement.get("description", ""),
            "durationSeconds": int(improvement.get("durationSeconds", 0) or 0),
            "ingredients": tuple(improvement.get("ingredients", ())),
        } for improvement in improvements_response.get("improvements", ())
          if improvement.get("available", False) and not improvement.get("done", False))
        if include_archival and bool(selected.get("isDefault")):
            daily_result = {"created": [], "failures": []}
            if self.data_engine.get_preference("auto_game_logbook", "false") == "true":
                daily_result = DailyProbeReportService(self.data_engine).generate_due(
                    probe_data.get("probes", ()),
                    automation["probeRoles"],
                    lambda candidate_id, payload: self.capabilities.probes.create_logbook_page(
                        candidate_id, payload
                    ),
                )
                if daily_result["created"]:
                    self._logbook_cache.clear()
            cached_logbook = self._logbook_cache.get(selected_id)
            if cached_logbook is None or now - cached_logbook[0] >= 300:
                cached_logbook = (
                    now,
                    self.logbook_view(selected_id, (selected,)),
                )
                self._logbook_cache[selected_id] = cached_logbook
            dashboard["logbook"] = cached_logbook[1]
            dashboard["logbook"]["dailyReportFailures"] = daily_result["failures"]
        else:
            cached_logbook = self._logbook_cache.get(selected_id)
            if cached_logbook is None or now - cached_logbook[0] >= 300:
                cached_logbook = (now, self.logbook_view(selected_id, (selected,)))
                self._logbook_cache[selected_id] = cached_logbook
            dashboard["logbook"] = cached_logbook[1]
        report(100, "Mission control ready")
        return dashboard

    def logbook_view(self, probe_id=None, probes=None):
        probe_id = probe_id or self._selected_probe_id
        probes = tuple(probes or ({"id": probe_id, "name": f"Probe {probe_id}"},))
        summaries = []
        self._logbook_page_probes = {}
        failures = []
        for probe in probes:
            candidate_id = probe.get("id")
            try:
                response = self.capabilities.probes.logbook_pages(candidate_id, limit=100)
            except requests.RequestException as error:
                failures.append({"probeId": candidate_id, "message": str(error)})
                continue
            reporter = DailyProbeReportService(self.data_engine)
            for page in response.get("pages", ()):
                item = reporter.annotate_page(page, candidate_id)
                item["sourceProbeId"] = candidate_id
                item["sourceProbeName"] = probe.get("name") or f"Probe {candidate_id}"
                summaries.append(item)
                self._logbook_page_probes[int(item["id"])] = candidate_id
        summaries.sort(key=lambda item: (item.get("updatedAt", ""), item.get("id", 0)), reverse=True)
        return {
            "pages": summaries,
            "focusedProbeId": probe_id,
            "failures": failures,
            "autoLoggingEnabled": self.data_engine.get_preference("auto_game_logbook", "false") == "true",
            "newDailyReportCount": sum(1 for item in summaries if item.get("isNewDailyReport")),
        }

    def get_logbook_page(self, page_id):
        owner = self._logbook_page_probes.get(int(page_id), self._selected_probe_id)
        response = self.capabilities.probes.get_logbook_page(owner, page_id)
        page = response.get("page", response)
        DailyProbeReportService(self.data_engine).mark_read(owner, page.get("title", ""))
        return page

    def create_logbook_page(self, payload):
        return self.capabilities.probes.create_logbook_page(self._selected_probe_id, payload)

    def update_logbook_page(self, page_id, payload):
        owner = self._logbook_page_probes.get(int(page_id), self._selected_probe_id)
        return self.capabilities.probes.update_logbook_page(owner, page_id, payload)

    def delete_logbook_page(self, page_id):
        owner = self._logbook_page_probes.get(int(page_id), self._selected_probe_id)
        return self.capabilities.probes.delete_logbook_page(owner, page_id)

    def send_message(self, payload):
        if self._selected_probe_id is None:
            raise RuntimeError("Select a probe before sending a message.")
        return self.capabilities.messaging.send(self._selected_probe_id, payload)

    def mark_message_read(self, message_id):
        if self._selected_probe_id is None:
            raise RuntimeError("Select a probe before updating a message.")
        return self.capabilities.messaging.mark_read(self._selected_probe_id, message_id)

    def automation_view(self, operations=None, probe_id=None):
        operations = operations or self._operations
        if probe_id is None:
            probe_id = self._selected_probe_id
        policy = ExecutionPolicyStore().load(probe_id)
        if operations is None or probe_id is None:
            self._prepared_commands = ()
            tasks = ()
        else:
            desired = DesiredStateStore(self.data_engine).load(probe_id)
            desired = self._reconcile_completed_autonomous_travel(
                operations,
                probe_id,
                desired,
            )
            desired, transport_tasks, transport_scope = self._reconcile_transport_operation(
                operations,
                probe_id,
                desired,
            )
            tasks = Planner(
                operations,
                desired,
            ).tasks()
            if transport_scope:
                tasks = [
                    replace(task, idempotency_scope=transport_scope)
                    if task.category == "travel" else task
                    for task in tasks
                ]
            tasks.extend(transport_tasks)
            tasks.sort(key=lambda task: task.priority)
            self._prepared_commands = CommandPreparer(
                operations, probe_id, policy,
            ).prepare(tasks)
        return {
            "probeId": probe_id,
            "mode": policy.mode.value,
            "liveExecutionEnabled": policy.live_execution_enabled,
            "allowedCommandTypes": [item.value for item in sorted(policy.allowed_command_types, key=lambda item: item.value)],
            "maxCommandsPerCycle": policy.max_commands_per_cycle,
            "queue": [self._prepared_view(item) for item in self._prepared_commands],
            "planning": [{
                "priority": task.priority,
                "action": task.action,
                "target": task.target or "",
                "reason": task.reason,
                "blockers": list(task.constraints),
            } for task in tasks],
            "emergencyStopActive": self.data_engine.emergency_stop_active(),
        }

    def _reconcile_completed_autonomous_travel(self, operations, probe_id, desired):
        """Retire a one-time destination once its safe endpoint is reached."""
        if desired.travel is None:
            return desired

        # A transport operation owns and continually advances its travel goal.
        # Its endpoint is a phase boundary, not completion of the durable loop.
        has_active_transport = any(
            item.metadata.get("template") == "round_trip_transport"
            and int(item.probe_id or -1) == int(probe_id)
            and item.state.value == "active"
            for item in OperationStore(self.data_engine).all()
        )
        if has_active_transport:
            return desired

        endpoint = desired.travel.target
        if operations.travel_safety.is_black_hole_sector(endpoint):
            endpoint = operations.travel_safety.nearest_safe_scut_sector(endpoint)
        current = operations.travel.current_sector()
        if (
            endpoint is None
            or current != endpoint
            or operations.travel_safety.is_black_hole_sector(current)
        ):
            return desired

        completed = replace(desired, travel=None)
        DesiredStateStore(self.data_engine).save(completed, probe_id)
        return completed

    def _reconcile_transport_operation(self, operations, probe_id, desired):
        """Advance one active route from authoritative live telemetry."""
        store = OperationStore(self.data_engine)
        operation = next((
            item for item in store.all()
            if item.metadata.get("template") == "round_trip_transport"
            and int(item.probe_id or -1) == int(probe_id)
            and item.state.value == "active"
        ), None)
        if operation is None:
            return desired, [], None

        cycle = operation.metadata.get("cycle") or {}
        source = SectorCoordinates.from_api(cycle["source"])
        destination = SectorCoordinates.from_api(cycle["destination"])
        return_point = SectorCoordinates.from_api(cycle["returnPoint"])
        current_sector = operations.travel.current_sector()
        probe = operations.world.probe
        fuel = probe.get("fuel") or {}
        fuel_amount = float(fuel.get("deuterium", 0) or 0)
        fuel_maximum = float(fuel.get("maxDeuterium", 0) or 0)
        load_amount = cycle.get("loadAmount")
        load_target = (
            float(load_amount)
            if load_amount is not None
            else fuel_maximum * float(cycle.get("loadUntilPercent", 100)) / 100
        )
        protected = (
            fuel_maximum * float(cycle.get("protectedDeuterium", 0)) / 100
            + (
                destination.distance_to(return_point)
                + int(cycle.get("reserveHops", 0) or 0)
            ) * operations.travel.fuel_cost()
        )
        phase = operation.metadata.get("transportPhase", "to_source")

        def travel_scope():
            circuit = int(operation.metadata.get("transportCircuit", 0) or 0)
            return f"transport:{operation.id}:circuit:{circuit}:phase:{phase}"

        def save_phase(value):
            nonlocal operation, phase
            if value == phase:
                return
            phase = value
            operation = replace(
                operation,
                metadata={**operation.metadata, "transportPhase": value},
            )
            store.save(operation)

        def save_desired(value):
            nonlocal desired
            if value != desired:
                desired = value
                DesiredStateStore(self.data_engine).save(desired, probe_id)

        # Bound the reconciliation loop so already-completed phases collapse
        # in one refresh without permitting an accidental busy loop.
        for _ in range(6):
            if phase == "to_source":
                if current_sector != source:
                    save_desired(replace(
                        desired,
                        travel=TravelGoal(source, "segmented"),
                    ))
                    return desired, [], travel_scope()
                save_phase("loading")
                continue

            if phase == "loading":
                if fuel_amount + 0.0001 < load_target:
                    target_percent = min(
                        100,
                        load_target / fuel_maximum * 100 if fuel_maximum else 100,
                    )
                    save_desired(replace(
                        desired,
                        travel=None,
                        fuel=FuelGoal(target_percent, desired.fuel.priority),
                    ))
                    return desired, [], None
                save_phase("to_destination")
                continue

            if phase == "to_destination":
                if current_sector != destination:
                    save_desired(replace(
                        desired,
                        travel=TravelGoal(destination, "segmented"),
                    ))
                    return desired, [], travel_scope()
                save_phase("unloading")
                continue

            if phase == "unloading":
                save_desired(replace(desired, travel=None))
                # A deuterium transfer is a five-minute game task. Do not
                # calculate another delivery from the same pre-transfer fuel
                # snapshot while one is still active; wait for it to finish,
                # then refresh source and destination capacity before
                # deciding whether another trip is needed.
                active_transfer = any(
                    "transfer" in task_type
                    and "deuterium" in task_type
                    and "probe" in task_type
                    for manny in operations.mannies.all()
                    if (
                        task_type := str(
                            operations.mannies._task_type(manny) or ""
                        ).lower().replace("-", "_").replace(" ", "_")
                    )
                )
                if active_transfer:
                    return desired, [], None
                transferable = max(0.0, fuel_amount - protected)
                if transferable < 0.01:
                    save_phase("to_return")
                    continue
                target_id = cycle.get("destinationProbeId")
                blockers = []
                target = None
                if target_id in {None, ""}:
                    blockers.append("destination_probe_not_selected")
                else:
                    try:
                        response = self.client.get_probe(int(target_id))
                        target = response.get("probe", response)
                    except Exception:
                        blockers.append("destination_probe_unavailable")
                target_fuel = (target or {}).get("fuel") or {}
                target_free = max(
                    0.0,
                    float(target_fuel.get("maxDeuterium", 0) or 0)
                    - float(target_fuel.get("deuterium", 0) or 0),
                )
                if target is not None and target.get("status") != "idle":
                    blockers.append("destination_probe_unavailable")
                if target is not None and target_free < 0.01:
                    # Remain docked and check again on the next transport tick.
                    return desired, [], None
                amount = min(transferable, target_free)
                return desired, [Task(
                    action="Transfer Deuterium",
                    reason=(
                        f"Fill probe {target_id} by up to {amount:.2f} ECE; "
                        f"preserve {protected:.2f} ECE for return and contingency."
                    ),
                    category="transport",
                    target=str(target_id or ""),
                    quantity=amount,
                    constraints=tuple(dict.fromkeys(blockers)),
                    resource_type="deuterium",
                    priority=1,
                )], None

            if phase == "to_return":
                if current_sector != return_point:
                    save_desired(replace(
                        desired,
                        travel=TravelGoal(return_point, "segmented"),
                    ))
                    return desired, [], travel_scope()
                if cycle.get("repeat", True):
                    phase = "to_source"
                    operation = replace(
                        operation,
                        metadata={
                            **operation.metadata,
                            "transportPhase": phase,
                            "transportCircuit": int(
                                operation.metadata.get("transportCircuit", 0) or 0
                            ) + 1,
                        },
                    )
                    store.save(operation)
                    continue
                save_desired(replace(desired, travel=None))
                store.save(operation.advance())
                return desired, [], None

        return desired, [], None

    @staticmethod
    def _prepared_view(prepared):
        command = prepared.command
        output_label = (
            command.payload.get("recipe")
            or command.metadata.get("model")
            or command.metadata.get("resource")
            or ""
        )
        return {
            "fingerprint": command.fingerprint,
            "type": command.type.value,
            "probeId": command.probe_id,
            "targetId": command.target_id,
            "reason": command.reason,
            "priority": command.priority,
            "disposition": prepared.disposition,
            "blockers": list(prepared.blockers),
            "warnings": [asdict(item) for item in prepared.warnings],
            "payload": command.payload,
            "metadata": command.metadata,
            "outputLabel": str(output_label).replace("_", " "),
        }

    def save_execution_policy(self, value):
        policy = ExecutionPolicy.from_dict(value)
        ExecutionPolicyStore().save(policy, self._selected_probe_id)
        return self.automation_view(probe_id=self._selected_probe_id)

    def run_automation_cycle(self, fingerprint=None, risk_acknowledged=False):
        policy = ExecutionPolicyStore().load(self._selected_probe_id)
        self.automation_view(probe_id=self._selected_probe_id)
        candidates = [
            item for item in self._prepared_commands
            if item.command.probe_id == self._selected_probe_id
            and (fingerprint is None or item.command.fingerprint == fingerprint)
        ]
        if not candidates:
            return {"status": "idle", "message": "No actionable automation command is queued."}
        if policy.mode == ExecutionMode.OBSERVE:
            return {"status": "observe_only", "message": "Observe mode never sends commands."}
        if policy.mode == ExecutionMode.APPROVE and fingerprint is None:
            return {"status": "awaiting_approval", "message": "Select and approve a queued command."}
        if policy.mode == ExecutionMode.AUTOMATIC:
            if fingerprint is not None:
                # Automatic commands normally execute only when their
                # disposition is ready. A risk acknowledgement is the one
                # operator-gated exception: execute the exact fingerprint the
                # operator acknowledged instead of filtering it back out as
                # awaiting_risk_acknowledgement.
                prepared = candidates[0]
                if prepared.disposition not in {
                    "ready", "awaiting_risk_acknowledgement"
                } or not risk_acknowledged:
                    return {
                        "status": "idle",
                        "message": "The selected automatic command still requires risk acknowledgement.",
                    }
                runtime = AutomationRuntime(
                    capabilities=self.capabilities,
                    data_engine=self.data_engine,
                    policy=policy,
                    dispatcher=CapabilityDispatcher(self.capabilities),
                    refresh=self._refresh_operations,
                )
                result = runtime.execute(
                    prepared,
                    risk_acknowledged=True,
                )
                return self._execution_result(prepared, result)
            candidates = [item for item in candidates if item.disposition == "ready"]
            if not candidates:
                return {
                    "status": "idle",
                    "message": "No allowlisted, unblocked command is ready for automatic execution.",
                }
            return self._run_replanning_automatic_cycle(
                policy, risk_acknowledged,
            )
        candidates = candidates[:1]
        runtime = AutomationRuntime(
            capabilities=self.capabilities,
            data_engine=self.data_engine,
            policy=policy,
            dispatcher=CapabilityDispatcher(self.capabilities),
            refresh=self._refresh_operations,
        )
        results = []
        for prepared in candidates:
            result = runtime.execute(
                prepared,
                approved=policy.mode == ExecutionMode.APPROVE,
                risk_acknowledged=risk_acknowledged,
            )
            results.append((prepared, result))
        succeeded = sum(result.status == "succeeded" for _, result in results)
        if len(results) > 1:
            status = "succeeded" if succeeded else results[-1][1].status
            message = f"{succeeded} of {len(results)} automation commands succeeded this cycle."
            return {
                "status": status,
                "message": message,
                "results": [self._execution_result(prepared, result) for prepared, result in results],
            }
        prepared, result = results[0]
        return self._execution_result(prepared, result)

    def _run_replanning_automatic_cycle(self, policy, risk_acknowledged=False):
        """Dispatch one fresh proposal at a time and replan after each order.

        Crafting and mining mutate the same resource and Manny availability
        ledger. Executing a queue prepared from one snapshot allows later
        commands to spend inputs already consumed by the first command and
        postpones newly-required mining until the next timer tick.
        """
        runtime = AutomationRuntime(
            capabilities=self.capabilities,
            data_engine=self.data_engine,
            policy=policy,
            dispatcher=CapabilityDispatcher(self.capabilities),
            refresh=self._refresh_operations,
        )
        attempted = set()
        results = []
        dependency_command = None
        for _ in range(policy.max_commands_per_cycle):
            # The previous execution's preflight already refreshed the world.
            # Rebuild the queue from that authoritative post-order state.
            self.automation_view(probe_id=self._selected_probe_id)
            prepared = dependency_command
            dependency_command = None
            if prepared is None:
                prepared = next((
                    item for item in self._prepared_commands
                    if item.command.probe_id == self._selected_probe_id
                    and item.disposition == "ready"
                    and self._cycle_attempt_key(item.command) not in attempted
                ), None)
            if prepared is None:
                # Manufacturing proposals are prepared before mining and claim
                # idle Mannys while the queue is built. Once each distinct
                # fabrication goal has had its chance this cycle, prepare the
                # remaining mining work alone so those stale planning claims do
                # not hide useful orders for otherwise-idle Mannys.
                prepared = self._prepare_next_cycle_mining(policy, attempted)
            if prepared is None:
                break
            attempted.add(self._cycle_attempt_key(prepared.command))
            result = runtime.execute(
                prepared,
                risk_acknowledged=risk_acknowledged,
            )
            results.append((prepared, result))
            if result.status != "succeeded":
                resource_type = self._missing_resource_from_failure(result)
                if resource_type:
                    dependency_command = self._prepare_dependency_mining(
                        resource_type, policy,
                    )
                # A rejected goal cannot freeze the priority walk. Mine its
                # dependency when possible; otherwise continue to the next
                # ready goal in this bounded cycle.
                continue
            self._refresh_operations(self._selected_probe_id)
        if not results:
            return {
                "status": "idle",
                "message": "No fresh allowlisted command remained ready after replanning.",
            }
        succeeded = sum(result.status == "succeeded" for _, result in results)
        if len(results) == 1:
            return self._execution_result(*results[0])
        last_status = results[-1][1].status
        return {
            "status": "succeeded" if succeeded and last_status == "succeeded" else last_status,
            "message": (
                f"{succeeded} of {len(results)} freshly replanned automation "
                "commands succeeded this cycle."
            ),
            "results": [
                self._execution_result(prepared, result)
                for prepared, result in results
            ],
        }

    @staticmethod
    def _cycle_attempt_key(command):
        """Identify one logical goal attempt while allowing parallel mining."""

        if command.type in {
            CommandType.MANNY_CRAFT,
            CommandType.ATOMIC_PRINTER_CRAFT,
        }:
            return (command.type.value, command.payload.get("recipe"))
        if command.type == CommandType.MANNY_MINE:
            resources = tuple(command.payload.get("resources") or ())
            return (command.type.value, resources, command.target_id)
        return (command.type.value, command.fingerprint)

    def _prepare_next_cycle_mining(self, policy, attempted):
        if getattr(self, "_operations", None) is None:
            return None
        desired = DesiredStateStore(self.data_engine).load(self._selected_probe_id)
        mining_tasks = tuple(
            task for task in Planner(self._operations, desired).tasks()
            if task.action in {"Mine Resource", "Mine Deuterium"}
        )
        prepared = CommandPreparer(
            self._operations, self._selected_probe_id, policy,
        ).prepare(mining_tasks)
        return next((
            item for item in prepared
            if item.disposition == "ready"
            and self._cycle_attempt_key(item.command) not in attempted
        ), None)

    @staticmethod
    def _missing_resource_from_failure(result):
        if result.status != "failed" or not isinstance(result.response, dict):
            return None
        detail = result.response.get("detail")
        error = detail.get("error", detail) if isinstance(detail, dict) else {}
        code = str(error.get("code", "")).casefold() if isinstance(error, dict) else ""
        if code == "insufficient_deuterium":
            return "deuterium"
        missing = error.get("missingResources", error.get("missing_resources")) if isinstance(error, dict) else None
        if isinstance(missing, dict) and missing:
            return next(iter(missing))
        return None

    def _prepare_dependency_mining(self, resource_type, policy):
        operations = self._operations
        target = operations.mining.best_target(resource_type) if operations else None
        if (
            target is None or not operations.mining.idle_mannies()
            or operations.world.probe.get("status") != "idle"
        ):
            return None
        desired = DesiredStateStore(self.data_engine).load(self._selected_probe_id)
        task = Task(
            action="Mine Deuterium" if resource_type == "deuterium" else "Mine Resource",
            reason=(
                f"The game rejected the preceding recipe because {resource_type.replace('_', ' ')} "
                "is insufficient. Mine the missing dependency before retrying that goal."
            ),
            category="mining",
            target=target["id"],
            quantity=min(float(target.get("available_amount", 0.55) or 0.55), 0.55),
            maximum_order_amount=desired.maximum_mining_order_amount,
            resource_type=resource_type,
            priority=1,
        )
        prepared = CommandPreparer(
            operations, self._selected_probe_id, policy,
        ).prepare((task,))
        return next((item for item in prepared if item.disposition == "ready"), None)

    def _execution_result(self, prepared, result):
        return {
            "status": result.status,
            "message": self._execution_message(result),
            "blockers": list(result.blockers),
            "fingerprint": prepared.command.fingerprint,
            "response": result.response,
        }

    @staticmethod
    def _execution_message(result):
        status = result.status.replace("_", " ").title()
        if result.status == "cancelled" and result.blockers:
            reasons = ", ".join(
                str(blocker).replace("_", " ")
                for blocker in result.blockers
            )
            return f"{status} · {reasons}"
        if result.status != "failed" or not isinstance(result.response, dict):
            return status
        detail = result.response.get("detail")
        if isinstance(detail, dict):
            error = detail.get("error", detail)
            if isinstance(error, dict):
                code = error.get("code")
                message = error.get("message")
                if code or message:
                    return " · ".join(str(item) for item in (code, message) if item)
        return str(result.response.get("error") or "Automation command failed")

    def _refresh_operations(self, probe_id):
        self.load(probe_id)
        return self._operations

    def preview_travel(self, probe_id, target, route_mode="segmented"):
        if self._operations is None or int(probe_id) != int(self._selected_probe_id):
            raise RuntimeError("Refresh the selected probe before planning travel.")
        destination = SectorCoordinates.from_api(target)
        blockers = self._operations.travel.travel_blockers(destination)
        desired = DesiredStateStore(self.data_engine).load(probe_id)
        assessment = self._operations.travel_safety.assess(
            destination,
            maximum_segment_distance=desired.maximum_safe_hop_distance,
        )
        if assessment is None:
            raise RuntimeError("Current sector is unavailable.")
        selected = next(
            (option for option in assessment.options if option.name == route_mode),
            assessment.recommended,
        )
        execution = selected.hops[0] if selected.hops else destination
        route_hops = tuple(selected.hops) or (destination,)
        acknowledgement_required = (
            assessment.acknowledgement_recommended
            if selected.name == assessment.recommended.name
            else selected.collision_risk_percent > 0 or selected.container_risk_percent > 0
        )
        return {
            "probeId": int(probe_id),
            "target": target,
            "targetLabel": f"FCC {destination.x} / {destination.y} / {destination.z}",
            "blockers": list(blockers),
            "canExecute": not blockers,
            "acknowledgementRequired": acknowledgement_required,
            "recommendedRoute": assessment.recommended.name,
            "selectedRoute": selected.name,
            "executionTarget": {"x": execution.x, "y": execution.y, "z": execution.z},
            "executionLabel": f"FCC {execution.x} / {execution.y} / {execution.z}",
            "routeHops": [
                {
                    "x": hop.x,
                    "y": hop.y,
                    "z": hop.z,
                    "label": f"FCC {hop.x} / {hop.y} / {hop.z}",
                }
                for hop in route_hops
            ],
            "hopCount": len(route_hops),
            "hazards": [asdict(hazard) for hazard in assessment.hazards],
            "options": [{
                "name": option.name,
                "hops": len(option.hops),
                "collisionRiskPercent": option.collision_risk_percent,
                "containerRiskPercent": option.container_risk_percent,
                "fuelCost": option.fuel_cost,
                "fuelSufficient": option.fuel_sufficient,
                "scutProtected": option.scut_protected,
            } for option in assessment.options],
        }

    def execute_travel(self, preview, risk_acknowledged=False):
        if preview.get("blockers"):
            raise RuntimeError("Travel is blocked: " + ", ".join(preview["blockers"]))
        if preview.get("acknowledgementRequired") and not risk_acknowledged:
            raise RuntimeError("Risk acknowledgement is required.")
        return self.capabilities.probes.move(preview["probeId"], preview["executionTarget"])

    def save_transport_cycle(self, value):
        coordinates = lambda key: SectorCoordinates.from_api(value[key])
        refuel_sectors = ()
        if value.get("refuelEnabled"):
            refuel_sectors = (coordinates("refuelSector"),)
        plan = RoundTripTransportPlan(
            probe_id=int(value["probeId"]),
            resource_type=str(value["resourceType"]),
            source=coordinates("source"),
            destination=coordinates("destination"),
            return_point=coordinates("returnPoint"),
            load_until_percent=float(value.get("loadUntilPercent", 100)),
            unload_until_percent=float(value.get("unloadUntilPercent", 0)),
            protected_deuterium=float(value.get("protectedDeuterium", 20)),
            reserve_hops=int(value.get("reserveHops", 1)),
            refuel_sectors=refuel_sectors,
            minimum_refuel_source_amount=float(value.get("minimumRefuelSourceAmount", 0)),
            repeat=bool(value.get("repeat", True)),
            source_probe_id=int(value["sourceProbeId"]) if value.get("sourceProbeId") not in {None, ""} else None,
            destination_probe_id=int(value["destinationProbeId"]) if value.get("destinationProbeId") not in {None, ""} else None,
            load_amount=float(value["loadAmount"]) if value.get("loadAmount") is not None else None,
            unload_amount=float(value["unloadAmount"]) if value.get("unloadAmount") is not None else None,
            load_source_mode=str(value.get("loadSourceMode", "probe")),
        )
        operation = OperationFactory.create(
            "round_trip_transport",
            probe_id=plan.probe_id,
            metadata={
                "cycle": plan.to_dict(),
                "loadingAction": plan.loading_action,
            },
        )
        OperationStore(self.data_engine).save(operation)
        return operation.to_dict()

    def start_transport_cycle(self, operation_id):
        store = OperationStore(self.data_engine)
        operation = store.get(operation_id)
        if (
            operation is None
            or operation.metadata.get("template") != "round_trip_transport"
        ):
            raise ValueError("Saved transport operation was not found.")
        if int(operation.probe_id or -1) != int(self._selected_probe_id):
            raise ValueError("Focus the transport probe assigned to this route before starting it.")
        if operation.state.value not in {"planned", "paused"}:
            raise ValueError(f"This transport route is already {operation.state.value}.")
        competing = next((
            item for item in store.all()
            if item.id != operation.id
            and item.metadata.get("template") == "round_trip_transport"
            and int(item.probe_id or -1) == int(operation.probe_id)
            and item.state.value == "active"
        ), None)
        if competing is not None:
            raise ValueError("This probe already has an active transport route. Remove it before starting another.")
        cycle = operation.metadata.get("cycle") or {}
        source = SectorCoordinates.from_api(cycle["source"])
        destination = SectorCoordinates.from_api(cycle["destination"])
        current_sector = (
            self._operations.travel.current_sector()
            if self._operations is not None
            else None
        )
        fuel = (
            self._operations.world.probe.get("fuel", {})
            if self._operations is not None
            else {}
        )
        fuel_amount = float(fuel.get("deuterium", 0) or 0)
        fuel_maximum = float(fuel.get("maxDeuterium", 0) or 0)
        load_amount = cycle.get("loadAmount")
        load_ready = (
            fuel_amount >= float(load_amount)
            if load_amount is not None
            else fuel_maximum > 0
            and fuel_amount / fuel_maximum * 100
            >= float(cycle.get("loadUntilPercent", 100))
        )
        # Reconcile the saved itinerary with live state at activation. A
        # tanker already at its source and above the load threshold must not
        # wait forever on two steps that are already complete.
        if current_sector == source and load_ready:
            next_target = destination
            phase = "to_destination"
        elif current_sector == source:
            next_target = None
            phase = "loading"
        elif current_sector == destination:
            next_target = None
            phase = "unloading"
        else:
            next_target = source
            phase = "to_source"
        current = DesiredStateStore(self.data_engine).load(operation.probe_id)
        DesiredStateStore(self.data_engine).save(
            replace(
                current,
                travel=(
                    TravelGoal(next_target, "segmented")
                    if next_target is not None
                    else None
                ),
            ),
            operation.probe_id,
        )
        operation = replace(
            operation.activate(),
            metadata={**operation.metadata, "transportPhase": phase},
        )
        store.save(operation)
        return operation.to_dict()

    def delete_transport_cycle(self, operation_id):
        store = OperationStore(self.data_engine)
        operation = store.get(operation_id)
        if (
            operation is None
            or operation.metadata.get("template") != "round_trip_transport"
        ):
            raise ValueError("Saved transport operation was not found.")
        if operation.state.value == "active":
            current = DesiredStateStore(self.data_engine).load(operation.probe_id)
            route_points = {
                SectorCoordinates.from_api(value)
                for key in ("source", "destination", "returnPoint")
                if (value := (operation.metadata.get("cycle") or {}).get(key))
            }
            if current.travel is not None and current.travel.target in route_points:
                DesiredStateStore(self.data_engine).save(
                    replace(current, travel=None),
                    operation.probe_id,
                )
        if not store.delete(operation_id):
            raise RuntimeError("Transport operation could not be removed.")
        return str(operation_id)

    def pause_transport_cycle(self, operation_id):
        store = OperationStore(self.data_engine)
        operation = store.get(operation_id)
        if (
            operation is None
            or operation.metadata.get("template") != "round_trip_transport"
        ):
            raise ValueError("Saved transport operation was not found.")
        if operation.state.value != "active":
            raise ValueError("Only an active transport route can be paused.")
        current = DesiredStateStore(self.data_engine).load(operation.probe_id)
        DesiredStateStore(self.data_engine).save(
            replace(current, travel=None),
            operation.probe_id,
        )
        return store.save(operation.pause("Paused by operator.")).to_dict()

    def rename_probe(self, name):
        return self.capabilities.probes.update(self._selected_probe_id, name=name.strip())

    def rename_container(self, container_id, label):
        return self.capabilities.storage.update_container(
            self._selected_probe_id, container_id, {"label": label.strip()},
        )

    def rename_manny(self, manny_id, name):
        return self.capabilities.mannies.rename(
            self._selected_probe_id, manny_id, name.strip(),
        )

    def update_container_rules(self, container_id, rules):
        return self.capabilities.storage.update_rules(
            self._selected_probe_id, container_id, rules,
        )

    def move_storage(self, payload):
        return self.capabilities.storage.move(self._selected_probe_id, payload)

    def jettison_inventory(self, item_id, amount=None, container_id=None):
        return self.capabilities.storage.jettison(
            self._selected_probe_id, item_id, amount, container_id,
        )

    def inventory_manny_action(self, action, manny_id, payload):
        allowed = {
            "detach-storage-container",
            "drop-storage-container",
            "recover-storage-container",
            "salvage",
            "transfer-deuterium-to-probe",
            "transfer-to-probe",
            "mine",
            "recall",
        }
        if action not in allowed:
            raise ValueError(f"Unsupported manual inventory action: {action}")
        return self.capabilities.mannies.start_task(
            self._selected_probe_id, manny_id, action, payload,
        )

    def manual_craft(self, recipe_id, manny_id):
        recipe = self.recipes.get(recipe_id)
        if recipe is None:
            raise ValueError(f"Unknown crafting recipe: {recipe_id}")
        if self._operations is None or self._selected_probe_id is None:
            raise RuntimeError("Refresh the focused probe before starting a manual build.")
        desired_state = DesiredStateStore(self.data_engine).load(self._selected_probe_id)
        planned_tasks = Planner(self._operations, desired_state).tasks()
        policy = ExecutionPolicyStore().load(self._selected_probe_id)
        conflicts = CommandPreparer(
            self._operations, self._selected_probe_id, policy,
        ).manual_manufacturing_blockers(recipe_id, planned_tasks)
        if conflicts:
            labels = {
                "item_reserved_by_higher_priority_goal": "crafted items",
                "resource_reserved_by_higher_priority_goal": "raw resources",
            }
            protected = " and ".join(labels.get(item, item) for item in conflicts)
            raise ValueError(
                f"Manual build blocked: {protected} required by this recipe are "
                "allocated to a higher-priority automation goal. Lower that goal, "
                "wait for surplus inputs, or change its target before crafting manually."
            )
        craftable_by = tuple(recipe.get("craftableBy", ()))
        if "manny" in craftable_by:
            if not manny_id:
                raise ValueError("Select an idle Manny for this manual build order.")
            return self.capabilities.mannies.start_task(
                self._selected_probe_id,
                manny_id,
                "craft",
                {"recipe": recipe_id},
            )
        if "atomic_3d_printer" in craftable_by:
            return self.capabilities.mannies.atomic_printer_craft(
                self._selected_probe_id, recipe_id,
            )
        raise ValueError("This recipe has no supported fabricator.")

    def manual_repair(self, manny_id, integrity_percent):
        if not manny_id:
            raise ValueError("Select an idle Manny for this repair order.")
        amount = float(integrity_percent)
        if not 0 < amount <= 100:
            raise ValueError("Repair amount must be between 1 and 100 percent.")
        return self.capabilities.mannies.start_task(
            self._selected_probe_id, manny_id, "repair",
            {"integrityPercent": amount},
        )

    def manual_upgrade(self, manny_id, improvement_id):
        if not manny_id:
            raise ValueError("Select an idle Manny for this probe upgrade.")
        if not improvement_id:
            raise ValueError("Select an available probe upgrade.")
        response = (self._operations.world.hazard_context.get("improvements") or {}) if self._operations else {}
        available = {
            item.get("id") for item in response.get("improvements", ())
            if item.get("available", False) and not item.get("done", False)
        }
        if improvement_id not in available:
            raise ValueError("That upgrade is locked, completed, or no longer available. Refresh Fleet and choose again.")
        return self.capabilities.mannies.start_task(
            self._selected_probe_id, manny_id, "improve-probe",
            {"improvement": improvement_id},
        )

    def scan_sector(self, target):
        response = self.capabilities.galaxy.observe_sector(target["x"], target["y"], target["z"])
        self.data_engine.record_sector_observation(self._selected_probe_id, response)
        sector = response.get("sector", response)
        result = {
            "target": target,
            "label": "FCC {x} / {y} / {z}".format(**target),
            "knowledgeLevel": sector.get("knowledgeLevel", "unknown"),
            "confidence": float(sector.get("confidence", 0) or 0),
            "objectCount": len(sector.get("objects", ()) or ()),
            "possibleObjects": sector.get("possibleObjects", ()),
            "estimatedObjects": sector.get("estimatedObjects", {}),
            "dangerEstimate": sector.get("dangerEstimate", sector.get("navigationalRisk", "unknown")),
            "scan": sector.get("scan", {}),
        }
        self._last_scan_result = result
        return result

    def scan_neighboring_sectors(self):
        if self._operations is None or self._selected_probe_id is None:
            raise RuntimeError("Refresh a focused probe before scanning neighboring sectors.")
        current = self._operations.travel.current_sector()
        if current is None:
            raise RuntimeError("The focused probe's current sector is unavailable.")
        results = []
        failures = []
        for neighbor in current.neighbors():
            target = {"x": neighbor.x, "y": neighbor.y, "z": neighbor.z}
            try:
                results.append(self.scan_sector(target))
            except requests.RequestException as error:
                failures.append({"target": target, "message": str(error)})
        summary = {
            "kind": "neighbor_scan",
            "label": f"NEIGHBOR SURVEY AROUND FCC {current.x} / {current.y} / {current.z}",
            "requested": 12,
            "scanned": len(results),
            "failed": len(failures),
            "discoveries": sum(item.get("objectCount", 0) > 0 for item in results),
            "results": results,
            "failures": failures,
        }
        self._last_scan_result = summary
        return summary

    def _auto_scan_explorer_arrival(self, probe_id, operations):
        role = next((
            row["role"] for row in FleetRoleService(self.data_engine).all("probe")
            if int(row["asset_id"]) == int(probe_id)
        ), None)
        current = operations.travel.current_sector()
        if role != "explorer" or current is None or operations.world.probe.get("status") != "idle":
            return None
        marker = f"{current.x}:{current.y}:{current.z}"
        key = f"explorer_neighbor_scan:{probe_id}"
        if self.data_engine.get_preference(key) == marker:
            return None
        result = self.scan_neighboring_sectors()
        if result["scanned"] == result["requested"]:
            self.data_engine.set_preference(key, marker)
            result["automatic"] = True
        return result

    def _initialize(self):
        if self._initialized:
            return
        self.api_version = self.client.ensure_compatible_api()
        self.recipes.load(self.client.get_crafting_recipes())
        self._initialized = True

    def _build_world(self, player, probe_data, probe, selected, mannies):
        if not selected.get("isReachable", True):
            return self.world_builder.build_limited(
                player, probe_data, probe, selected["name"], mannies,
            )
        try:
            snapshot, snapshot_path = self.snapshot_manager.refresh_sector(selected["id"])
        except requests.HTTPError as error:
            if error.response is None or error.response.status_code != 400:
                raise
            return self.world_builder.build_limited(
                player, probe_data, probe, selected["name"], mannies,
            )
        return self.world_builder.build(
            player,
            probe_data,
            probe,
            snapshot,
            snapshot_path,
            selected["name"],
            mannies,
        )

    @staticmethod
    def _player_view(payload):
        player = payload.get("player", payload)
        return {
            "id": player.get("id"),
            "displayName": player.get("displayName") or player.get("name") or "Commander",
        }

    @staticmethod
    def _probe_option(probe):
        sector = probe.get("sector") or {}
        coordinates = sector.get("relative") or sector.get("relativeCoordinates") or {}
        label = "SECTOR UNKNOWN"
        if coordinates:
            label = "FCC {x} / {y} / {z}".format(
                x=coordinates.get("x", "?"),
                y=coordinates.get("y", "?"),
                z=coordinates.get("z", "?"),
            )
        return {
            "id": int(probe["id"]),
            "name": probe.get("name", f"Probe {probe['id']}"),
            "model": probe.get("model", "generic"),
            "status": (probe.get("movement") or probe.get("travel") or {}).get("phase") or (probe.get("movement") or probe.get("travel") or {}).get("status") or probe.get("status", "unknown"),
            "sectorLabel": label,
            "isReachable": probe.get("isReachable", True),
            "isDefault": probe.get("isDefault", False),
            "movement": MissionControlViewModelBuilder._movement_view(probe),
            "velocity": probe.get("velocity", probe.get("velocityC", 0)),
            "sensorMode": probe.get("sensorMode") or probe.get("sensors") or "unknown",
            "deuterium": probe.get("deuterium", probe.get("fuel", 0)),
            "maxDeuterium": probe.get("maxDeuterium", probe.get("maxFuel", 100)),
        }

    def save_fleet_naming_policy(self, policy, apply_existing=False):
        """Persist a naming scheme and rename either existing or newly seen assets."""

        policy = dict(policy or {})
        policy.setdefault("enabled", False)
        policy.setdefault("inferPrefix", False)
        policy.setdefault("prefix", "SKUNKWORKS")
        policy.setdefault("probeTemplate", "{prefix}-{number:02d}")
        policy.setdefault("mannyTemplate", "{probe}-M{number:02d}")
        response = self.capabilities.probes.list()
        probes = list(response.get("probes", ()))
        try:
            seen = json.loads(self.data_engine.get_preference("fleet_naming_seen") or "{}")
        except (TypeError, ValueError):
            seen = {}
        seen_probe_ids = {str(value) for value in seen.get("probes", ())}
        seen_manny_ids = {str(value) for value in seen.get("mannies", ())}
        prefix = str(policy.get("prefix") or "SKUNKWORKS").strip()
        if policy.get("inferPrefix") and probes:
            reference_probe = next((probe for probe in probes if probe.get("isDefault")), probes[0])
            current_name = str(reference_probe.get("name") or "").strip()
            inferred = re.sub(r"(?:[-_ ]?\d+)+$", "", current_name).strip("-_ ")
            if inferred:
                prefix = inferred
                policy["prefix"] = prefix
                self.data_engine.set_preference("fleet_naming_policy", json.dumps(policy))

        renamed_probes = 0
        renamed_mannies = 0
        current_probe_ids = set()
        current_manny_ids = set()
        for number, probe in enumerate(sorted(probes, key=lambda row: int(row["id"])), 1):
            probe_key = str(probe["id"])
            current_probe_ids.add(probe_key)
            values = {
                "prefix": prefix,
                "number": number,
                "model": str(probe.get("model") or "generic").replace("_", "-"),
                "probe": str(probe.get("name") or f"Probe-{number}"),
            }
            new_probe_name = str(policy["probeTemplate"]).format_map(values).strip()
            rename_probe = apply_existing or (seen_probe_ids and probe_key not in seen_probe_ids)
            if rename_probe and new_probe_name and new_probe_name != probe.get("name"):
                self.capabilities.probes.update(probe["id"], name=new_probe_name)
                renamed_probes += 1
            values["probe"] = (new_probe_name if rename_probe else values["probe"])
            manny_response = self.capabilities.mannies.list(probe["id"])
            for manny_number, manny in enumerate(manny_response.get("mannies", ()), 1):
                manny_key = f"{probe_key}:{manny['id']}"
                current_manny_ids.add(manny_key)
                manny_values = dict(values, number=manny_number)
                new_manny_name = str(policy["mannyTemplate"]).format_map(manny_values).strip()
                rename_manny = apply_existing or (seen_manny_ids and manny_key not in seen_manny_ids)
                if rename_manny and new_manny_name and new_manny_name != manny.get("name"):
                    self.capabilities.mannies.rename(probe["id"], manny["id"], new_manny_name)
                    renamed_mannies += 1
        self.data_engine.set_preference("fleet_naming_policy", json.dumps(policy))
        self.data_engine.set_preference("fleet_naming_seen", json.dumps({
            "probes": sorted(current_probe_ids), "mannies": sorted(current_manny_ids),
        }))
        return {
            "status": "applied", "renamedProbes": renamed_probes,
            "renamedMannies": renamed_mannies, "policy": policy,
        }


class _WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)


class _RefreshWorker(QRunnable):
    def __init__(self, service, probe_id):
        super().__init__()
        self.service = service
        self.probe_id = probe_id
        self.signals = _WorkerSignals()

    def run(self):
        try:
            try:
                payload = self.service.load(self.probe_id, progress=self.signals.progress.emit)
            except TypeError as error:
                if "progress" not in str(error):
                    raise
                payload = self.service.load(self.probe_id)
        except Exception as error:  # UI boundary: preserve the process and report.
            traceback.print_exc()
            self.signals.failed.emit(str(error) or type(error).__name__)
        else:
            self.signals.succeeded.emit(payload)


class _CompatibilityWorker(QRunnable):
    """Check the unmetered API-version endpoint without refreshing fleet data."""

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.signals = _WorkerSignals()

    def run(self):
        try:
            version = self.client.get_api_version()
            self.client.api_version = version
        except Exception as error:
            self.signals.failed.emit(str(error) or type(error).__name__)
            return
        self.signals.succeeded.emit({
            "version": version,
            "compatible": MINIMUM_API_VERSION <= version <= MAXIMUM_API_VERSION,
        })


class _FleetNamingWorker(QRunnable):
    def __init__(self, policy, apply_existing, service_factory=MissionControlDataService):
        super().__init__()
        self.policy = dict(policy or {})
        self.apply_existing = bool(apply_existing)
        self.service_factory = service_factory
        self.signals = _WorkerSignals()

    def run(self):
        try:
            service = self.service_factory()
            result = service.save_fleet_naming_policy(self.policy, self.apply_existing)
        except Exception as error:
            traceback.print_exc()
            self.signals.failed.emit(str(error) or type(error).__name__)
            return
        self.signals.succeeded.emit(result)


class _FleetAutomationWorker(QRunnable):
    """Run eligible probe schedulers without changing the operator's focus."""

    def __init__(self, probe_ids, service_factory=MissionControlDataService):
        super().__init__()
        self.probe_ids = tuple(int(value) for value in probe_ids)
        self.service_factory = service_factory
        self.signals = _WorkerSignals()

    def run(self):
        results = []
        try:
            for probe_id in self.probe_ids:
                policy = ExecutionPolicyStore().load(probe_id)
                if not (
                    policy.mode == ExecutionMode.AUTOMATIC
                    and policy.live_execution_enabled
                ):
                    continue
                service = self.service_factory()
                try:
                    service.load(probe_id, include_archival=False)
                except TypeError:
                    # Preserve lightweight test/service doubles with the older
                    # one-argument protocol.
                    service.load(probe_id)
                result = service.run_automation_cycle(None, False)
                results.append({"probeId": probe_id, "result": result})
        except Exception as error:
            traceback.print_exc()
            self.signals.failed.emit(str(error) or type(error).__name__)
            return
        self.signals.succeeded.emit(results)


class _AutomationCycleWorker(QRunnable):
    """Execute an operator-requested cycle without blocking the Qt UI thread."""

    def __init__(
        self, probe_id, fingerprint=None, risk_acknowledged=False,
        service_factory=MissionControlDataService,
    ):
        super().__init__()
        self.probe_id = int(probe_id)
        self.fingerprint = fingerprint
        self.risk_acknowledged = bool(risk_acknowledged)
        self.service_factory = service_factory
        self.signals = _WorkerSignals()

    def run(self):
        try:
            service = self.service_factory()
            try:
                service.load(self.probe_id, include_archival=False)
            except TypeError:
                service.load(self.probe_id)
            result = service.run_automation_cycle(
                self.fingerprint, self.risk_acknowledged,
            )
        except Exception as error:
            traceback.print_exc()
            self.signals.failed.emit(str(error) or type(error).__name__)
            return
        self.signals.succeeded.emit(result)


class MissionControlController(QObject):
    """Asynchronous QObject consumed by App.qml."""

    dashboardChanged = Signal()
    availableProbesChanged = Signal()
    focusedProbeIdChanged = Signal()
    refreshingChanged = Signal()
    errorChanged = Signal()
    emergencyStopChanged = Signal()
    credentialsChanged = Signal()
    onboardingChanged = Signal()
    credentialMessageChanged = Signal()
    startupLoadingChanged = Signal()
    loadingProgressChanged = Signal()

    def __init__(self, service=None, thread_pool=None, settings_engine=None, credential_store=None):
        super().__init__()
        self.service = service
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._dashboard = {}
        self._available_probes = []
        self._probe_snapshot_cache = {}
        self._focused_probe_id = -1
        self._refreshing = False
        self._error = ""
        self._emergency_stop = False
        self._worker = None
        self._pending_probe_id = None
        self._refresh_target_id = None
        self.settings_engine = settings_engine or (service.data_engine if service is not None and hasattr(service, "data_engine") else DataEngine())
        self.credential_store = credential_store or CredentialStore()
        self._credential_message = ""
        self._startup_loading = True
        self._loading_progress = 0
        self._loading_status = "Preparing secure connection"
        self._automation_timer = QTimer(self)
        self._automation_timer.setInterval(5 * 60_000)
        self._automation_timer.timeout.connect(self._automation_tick)
        self._automation_after_refresh = False
        # Automatic mode should not sit visibly READY for a full timer interval
        # after application startup. Consume this once after the first
        # authoritative dashboard has loaded.
        self._initial_automation_cycle_pending = True
        self._fleet_automation_worker = None
        self._automation_cycle_worker = None
        self._compatibility_timer = QTimer(self)
        self._compatibility_timer.setInterval(6 * 60 * 60 * 1000)
        self._compatibility_timer.timeout.connect(self._start_compatibility_check)
        self._compatibility_worker = None
        self._api_compatible = True
        self._retry_timer = QTimer(self)
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._retry_rate_limited_refresh)
        self._retry_probe_id = None
        self._naming_worker = None
        self._naming_last_audit = 0.0

    @Property("QVariantMap", notify=dashboardChanged)
    def dashboard(self):
        return self._dashboard

    @Property("QVariantList", notify=availableProbesChanged)
    def availableProbes(self):
        return self._available_probes

    @Property(int, notify=focusedProbeIdChanged)
    def focusedProbeId(self):
        return self._focused_probe_id

    @Property(bool, notify=refreshingChanged)
    def refreshing(self):
        return self._refreshing

    @Property(bool, notify=startupLoadingChanged)
    def startupLoading(self):
        return self._startup_loading

    @Property(int, notify=loadingProgressChanged)
    def loadingProgress(self):
        return self._loading_progress

    @Property(str, notify=loadingProgressChanged)
    def loadingStatus(self):
        return self._loading_status

    @Property(str, notify=errorChanged)
    def error(self):
        return self._error

    @Property(bool, notify=emergencyStopChanged)
    def emergencyStopActive(self):
        return self._emergency_stop

    @Property(bool, notify=credentialsChanged)
    def credentialConfigured(self):
        return bool(self.credential_store.get())

    @Property(str, notify=credentialsChanged)
    def credentialSource(self):
        return self.credential_store.source()

    @Property(bool, notify=onboardingChanged)
    def onboardingRequired(self):
        return self.settings_engine.get_preference("onboarding_complete") != "true"

    @Property(str, notify=credentialMessageChanged)
    def credentialMessage(self):
        return self._credential_message

    @Slot()
    def start(self):
        if self.onboardingRequired:
            self._set_startup_loading(False)
            return
        if not self.credentialConfigured:
            self._set_credential_message("Configure an API key in Settings.")
            self._set_startup_loading(False)
            return
        self.refresh()

    @Slot(str)
    def saveApiKey(self, api_key):
        try:
            self.credential_store.save(api_key)
        except Exception as error:
            self._set_credential_message(str(error) or type(error).__name__)
            return
        self.service = None
        self.credentialsChanged.emit()
        self._set_credential_message("API key saved securely in the operating-system credential vault.")
        self._update_credential_dashboard()

    @Slot()
    def testApiKey(self):
        api_key = self.credential_store.get()
        if not api_key:
            self._set_credential_message("Save an API key before testing the connection.")
            return
        try:
            client = GameClient(api_key=api_key)
            version = client.ensure_compatible_api()
            player = client.get_player().get("player", {})
        except Exception as error:
            self._set_credential_message("Connection failed: " + (str(error) or type(error).__name__))
            return
        self._set_credential_message(
            f"Connection verified · API v{version} · {player.get('displayName') or player.get('name') or 'account authenticated'}"
        )
        self._update_credential_dashboard()

    @Slot()
    def removeApiKey(self):
        try:
            self.credential_store.delete()
        except Exception as error:
            self._set_credential_message(str(error) or type(error).__name__)
            return
        self.service = None
        self.credentialsChanged.emit()
        self._set_credential_message("Stored API key removed.")
        self._update_credential_dashboard()

    @Slot()
    def completeOnboarding(self):
        if not self.credentialConfigured:
            self._set_credential_message("An API key is required before setup can finish.")
            return
        self.settings_engine.set_preference("onboarding_complete", "true")
        self.onboardingChanged.emit()
        self.refresh()

    @Slot()
    def resetOnboarding(self):
        self.settings_engine.set_preference("onboarding_complete", "false")
        self.onboardingChanged.emit()

    def _open_document(self, relative_path):
        roots = [Path(__file__).resolve().parents[2], Path(sys.executable).resolve().parent]
        if getattr(sys, "_MEIPASS", None):
            roots.insert(0, Path(sys._MEIPASS))
        path = next((root / relative_path for root in roots if (root / relative_path).is_file()), roots[0] / relative_path)
        if not path.is_file():
            self._set_error(f"Documentation file is missing: {path}")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            self._set_error(f"The operating system could not open: {path.name}")

    @Slot()
    def openOperatorManual(self):
        self._open_document(Path("docs/user-guide/Skunkworks_Operator_Manual.docx"))

    @Slot()
    def openChangeLog(self):
        self._open_document(Path("docs/user-guide/CHANGELOG.md"))

    @Slot()
    def checkForUpdates(self):
        url = QUrl("https://github.com/Ziegenbagel/skunkworks/releases/latest")
        if not QDesktopServices.openUrl(url):
            self._set_error("The operating system could not open the Skunkworks release page.")

    @Slot()
    def openDiagnosticLogs(self):
        directory = diagnostic_log_directory()
        directory.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(directory))):
            self._set_error("The operating system could not open the diagnostic log folder.")

    @Slot("QVariantMap")
    def saveExecutionPolicy(self, value):
        if self.service is None:
            self._set_error("Refresh live account data before configuring automation.")
            return
        try:
            runtime = self.service.save_execution_policy(self._qt_safe(value))
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._dashboard["automationRuntime"] = self._qt_safe(runtime)
        self._configure_automation_timer(runtime)
        self._set_error("")
        self.dashboardChanged.emit()

    @Slot("QVariantMap", bool)
    def saveFleetNamingPolicy(self, policy, apply_existing=False):
        default_probe_id = self._dashboard.get("defaultProbeId")
        if default_probe_id is None or int(self._focused_probe_id) != int(default_probe_id):
            self._set_error("Fleet auto-naming can only be configured while the main/default probe is focused.")
            return
        if self._naming_worker is not None:
            return
        worker = _FleetNamingWorker(self._qt_safe(policy), apply_existing)
        worker.signals.succeeded.connect(self._accept_fleet_naming)
        worker.signals.failed.connect(self._reject_fleet_naming)
        self._naming_worker = worker
        self.thread_pool.start(worker)

    @Slot(object)
    def _accept_fleet_naming(self, result):
        self._naming_worker = None
        self._set_error("")
        self._start_refresh(self._focused_probe_id if self._focused_probe_id >= 0 else None)

    @Slot(str)
    def _reject_fleet_naming(self, message):
        self._naming_worker = None
        self._set_error(message)

    @Slot()
    def runAutomationCycle(self):
        self._start_automation_cycle(None, False)

    @Slot(str, bool)
    def approveAutomationCommand(self, fingerprint, risk_acknowledged=False):
        if risk_acknowledged and self._is_queued_travel_command(fingerprint):
            try:
                store = DesiredStateStore(self.service.data_engine)
                current = store.load(self._focused_probe_id)
                if current.travel is not None:
                    store.save(
                        replace(
                            current,
                            travel=replace(
                                current.travel,
                                risk_acknowledged=True,
                            ),
                        ),
                        self._focused_probe_id,
                    )
                    automation = dict(self._dashboard.get("automation", {}))
                    target = dict(automation.get("travelTarget", {}))
                    target["riskAcknowledged"] = True
                    automation["travelTarget"] = target
                    self._dashboard["automation"] = automation
            except Exception as error:
                self._set_error(str(error) or type(error).__name__)
                return
        self._start_automation_cycle(fingerprint, risk_acknowledged)

    def _is_queued_travel_command(self, fingerprint):
        return any(
            str(item.get("fingerprint", "")) == str(fingerprint)
            and str(item.get("type", "")) == CommandType.MOVE_PROBE.value
            for item in self._dashboard.get("automationRuntime", {}).get("queue", ())
        )

    def _start_automation_cycle(self, fingerprint, risk_acknowledged):
        if (
            self._focused_probe_id < 0 or self._refreshing
            or self._automation_cycle_worker is not None
            or not self._api_compatible
        ):
            return
        worker = _AutomationCycleWorker(
            self._focused_probe_id, fingerprint, risk_acknowledged,
        )
        worker.signals.succeeded.connect(self._accept_automation_cycle)
        worker.signals.failed.connect(self._reject_automation_cycle)
        self._automation_cycle_worker = worker
        self.thread_pool.start(worker)

    @Slot(object)
    def _accept_automation_cycle(self, result):
        self._automation_cycle_worker = None
        runtime = dict(self._dashboard.get("automationRuntime", {}))
        runtime["lastResult"] = self._qt_safe(result)
        self._dashboard["automationRuntime"] = runtime
        self.dashboardChanged.emit()
        self._start_refresh(self._focused_probe_id)

    @Slot(str)
    def _reject_automation_cycle(self, message):
        self._automation_cycle_worker = None
        self._set_error("Automation cycle failed: " + message)

    def _run_automation(self, fingerprint, risk_acknowledged):
        if self.service is None or self._refreshing or not self._api_compatible:
            if not self._api_compatible:
                self._set_error("Automation is paused until the current game API version has been reviewed.")
            return
        try:
            result = self.service.run_automation_cycle(fingerprint, risk_acknowledged)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        runtime = dict(self._dashboard.get("automationRuntime", {}))
        runtime["lastResult"] = self._qt_safe(result)
        self._dashboard["automationRuntime"] = runtime
        self.dashboardChanged.emit()
        if result.get("status") in {"succeeded", "cancelled", "failed", "expired"}:
            self._start_refresh(self._focused_probe_id)

    def _automation_tick(self):
        if self._emergency_stop or self._refreshing or self._fleet_automation_worker is not None:
            return
        probe_ids = [item.get("id") for item in self._available_probes if item.get("id")]
        if not probe_ids and self._focused_probe_id >= 0:
            probe_ids = [self._focused_probe_id]
        eligible = []
        for probe_id in probe_ids:
            policy = ExecutionPolicyStore().load(int(probe_id))
            if policy.mode == ExecutionMode.AUTOMATIC and policy.live_execution_enabled:
                eligible.append(int(probe_id))
        if not eligible:
            return
        worker = _FleetAutomationWorker(eligible)
        worker.signals.succeeded.connect(self._accept_fleet_automation)
        worker.signals.failed.connect(self._reject_fleet_automation)
        self._fleet_automation_worker = worker
        self.thread_pool.start(worker)

    @Slot(object)
    def _accept_fleet_automation(self, results):
        self._fleet_automation_worker = None
        runtime = dict(self._dashboard.get("automationRuntime", {}))
        runtime["fleetResults"] = self._qt_safe(results)
        runtime["lastFleetCycleProbeCount"] = len(results)
        focused_result = next((
            item.get("result") for item in results
            if int(item.get("probeId", -1)) == int(self._focused_probe_id)
        ), None)
        if focused_result is not None:
            runtime["lastResult"] = self._qt_safe(focused_result)
        self._dashboard["automationRuntime"] = runtime
        self.dashboardChanged.emit()
        self._start_refresh(self._focused_probe_id if self._focused_probe_id >= 0 else None)

    @Slot(str)
    def _reject_fleet_automation(self, message):
        self._fleet_automation_worker = None
        self._set_error("Fleet automation cycle failed: " + message)
        self._start_refresh(self._focused_probe_id if self._focused_probe_id >= 0 else None)

    def _start_compatibility_check(self):
        if self.service is None or self._compatibility_worker is not None:
            return
        worker = _CompatibilityWorker(self.service.client)
        worker.signals.succeeded.connect(self._accept_compatibility)
        worker.signals.failed.connect(self._reject_compatibility)
        self._compatibility_worker = worker
        self.thread_pool.start(worker)

    @Slot(object)
    def _accept_compatibility(self, result):
        self._compatibility_worker = None
        version = int(result.get("version", -1))
        compatible = bool(result.get("compatible", False))
        self._api_compatible = compatible
        compatibility = {
            "checked": True,
            "compatible": compatible,
            "serverVersion": version,
            "supportedMinimum": MINIMUM_API_VERSION,
            "supportedMaximum": MAXIMUM_API_VERSION,
            "checkIntervalHours": 6,
        }
        if self._dashboard:
            self._dashboard["compatibility"] = compatibility
            if not compatible:
                self._dashboard["connection"] = "stale"
                self._dashboard["connectionLabel"] = "API REVIEW REQUIRED"
            self.dashboardChanged.emit()
        if compatible:
            return
        self._automation_timer.stop()
        self._set_error(
            f"Von Neumann Game API v{version} is newer than the reviewed "
            f"Skunkworks range v{MINIMUM_API_VERSION}–v{MAXIMUM_API_VERSION}. "
            "Live commands and automation are paused pending compatibility review."
        )

    @Slot(str)
    def _reject_compatibility(self, message):
        self._compatibility_worker = None
        if self._dashboard:
            self._dashboard["compatibility"] = {
                "checked": False,
                "compatible": self._api_compatible,
                "error": message,
                "checkIntervalHours": 6,
            }
            self.dashboardChanged.emit()

    def _configure_automation_timer(self, runtime):
        enabled = runtime.get("mode") == "automatic" and runtime.get("liveExecutionEnabled")
        active_transport = any(
            item.get("state") == "active"
            for item in self._dashboard.get("automation", {}).get(
                "transportCycles", ()
            )
        )
        self._automation_timer.setInterval(
            60_000 if active_transport else 5 * 60_000
        )
        if not enabled:
            for probe in self._available_probes:
                policy = ExecutionPolicyStore().load(int(probe["id"]))
                if policy.mode == ExecutionMode.AUTOMATIC and policy.live_execution_enabled:
                    enabled = True
                    break
        if enabled and not self._automation_timer.isActive():
            self._automation_timer.start()
        elif not enabled:
            self._automation_timer.stop()

    def _set_credential_message(self, message):
        if message == self._credential_message:
            return
        self._credential_message = message
        self.credentialMessageChanged.emit()

    def _update_credential_dashboard(self):
        if not self._dashboard:
            return
        self._dashboard["credentials"] = {
            "configured": self.credentialConfigured,
            "source": self.credentialSource,
            "message": self.credentialMessage,
        }
        self.dashboardChanged.emit()

    @Slot()
    def refresh(self):
        self._start_refresh(self._focused_probe_id if self._focused_probe_id >= 0 else None)

    @Slot(int)
    def selectProbe(self, probe_id):
        if self._refreshing:
            self._pending_probe_id = probe_id
            return
        if probe_id == self._focused_probe_id:
            return
        self._start_refresh(probe_id)

    @Slot(bool)
    def setEmergencyStop(self, active):
        if self.service is None:
            try:
                self.service = MissionControlDataService()
            except Exception as error:
                self._set_error(str(error) or type(error).__name__)
                return
        self.service.data_engine.set_emergency_stop(active)
        if active != self._emergency_stop:
            self._emergency_stop = active
            self.emergencyStopChanged.emit()

    @Slot("QVariantMap")
    def saveAutomationSettings(self, settings):
        if self.service is None:
            self.service = MissionControlDataService()
        try:
            state = DesiredState.from_dict(self._qt_safe(settings))
            DesiredStateStore(self.service.data_engine).save(
                state, self._focused_probe_id,
            )
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        automation.update(self._qt_safe(state.to_dict()))
        self._dashboard["automation"] = automation
        runtime = self.service.automation_view()
        self._dashboard["automationRuntime"] = self._qt_safe(runtime)
        self._configure_automation_timer(runtime)
        self._set_error("")
        self.dashboardChanged.emit()
        # A saved goal is an explicit request to replan. Refresh authoritative
        # inventory/task state first, then let automatic mode evaluate without
        # waiting for the next 60-second timer tick.
        runtime_mode = runtime.get("mode")
        if runtime_mode == "automatic" and runtime.get("liveExecutionEnabled"):
            self._automation_after_refresh = True
        if not self._refreshing:
            self._start_refresh(self._focused_probe_id)

    @Slot(str, str)
    def queueManualCraft(self, recipe_id, manny_id):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Select and refresh a probe before queuing a manual build.")
            return
        try:
            self.service.manual_craft(recipe_id, manny_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._set_error("")
        self._start_refresh(self._focused_probe_id)

    @Slot(str, float)
    def queueManualRepair(self, manny_id, integrity_percent):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Select and refresh a probe before ordering repairs.")
            return
        try:
            self.service.manual_repair(manny_id, integrity_percent)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._set_error("")
        self._start_refresh(self._focused_probe_id)

    @Slot(str, str)
    def queueManualUpgrade(self, manny_id, improvement_id):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Select and refresh a probe before ordering an upgrade.")
            return
        try:
            self.service.manual_upgrade(manny_id, improvement_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._set_error("")
        self._start_refresh(self._focused_probe_id)

    @Slot(int, str)
    def assignProbeRole(self, probe_id, role):
        if self.service is None:
            self.service = MissionControlDataService()
        default_probe_id = self._dashboard.get("defaultProbeId")
        if default_probe_id is None or int(self._focused_probe_id) != int(default_probe_id):
            self._set_error("Probe roles can only be managed while the main/default probe is focused.")
            return
        try:
            FleetRoleService(self.service.data_engine).assign("probe", probe_id, role)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        roles = dict(automation.get("probeRoles", {}))
        roles[str(probe_id)] = role
        automation["probeRoles"] = roles
        self._dashboard["automation"] = automation
        self.dashboardChanged.emit()

    @Slot(int, int, int, str)
    def previewTravel(self, x, y, z, route_mode="segmented"):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Select and refresh a probe before planning travel.")
            return
        try:
            preview = self.service.preview_travel(
                self._focused_probe_id, {"x": x, "y": y, "z": z}, route_mode,
            )
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._dashboard["travelPreview"] = self._qt_safe(preview)
        self._set_error("")
        self.dashboardChanged.emit()

    @Slot(bool)
    def executeTravel(self, risk_acknowledged=False):
        preview = self._dashboard.get("travelPreview")
        if not preview or self.service is None:
            self._set_error("Preview a route before confirming travel.")
            return
        try:
            self.service.execute_travel(preview, risk_acknowledged)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._dashboard["travelPreview"] = {}
        self.dashboardChanged.emit()
        self._start_refresh(self._focused_probe_id)

    @Slot()
    def cancelTravel(self):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Select and refresh a probe before cancelling movement.")
            return
        try:
            self.service.capabilities.probes.cancel_move(self._focused_probe_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._set_error("")
        self._start_refresh(self._focused_probe_id)

    @Slot(int, int, int)
    def scanSector(self, x, y, z):
        if self.service is None:
            self._set_error("Refresh live account data before scanning.")
            return
        try:
            result = self.service.scan_sector({"x": x, "y": y, "z": z})
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        navigation = dict(self._dashboard.get("navigation", {}))
        navigation["scanResult"] = self._qt_safe(result)
        self._dashboard["navigation"] = navigation
        self._set_error("")
        self.dashboardChanged.emit()
        if result.get("objectCount", 0) > 0:
            self._maybe_auto_log(
                f"discovery:{result.get('label')}:{result.get('knowledgeLevel')}:{result.get('objectCount')}",
                f"Skunkworks discovery report · {result.get('label')}",
                (
                    f"Automated survey report for {result.get('label')}.\n\n"
                    f"Knowledge: {result.get('knowledgeLevel')}\n"
                    f"Confidence: {result.get('confidence', 0) * 100:.0f}%\n"
                    f"Known objects: {result.get('objectCount', 0)}\n"
                    f"Navigational risk: {result.get('dangerEstimate', 'unknown')}\n\n"
                    "Generated by Skunkworks because automatic game-logbook reporting is enabled."
                ),
            )
        if not self._refreshing:
            self._start_refresh(self._focused_probe_id)

    @Slot()
    def scanNeighboringSectors(self):
        if self.service is None:
            self._set_error("Refresh live account data before scanning.")
            return
        try:
            result = self.service.scan_neighboring_sectors()
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        navigation = dict(self._dashboard.get("navigation", {}))
        navigation["scanResult"] = self._qt_safe(result)
        self._dashboard["navigation"] = navigation
        self._set_error("")
        self.dashboardChanged.emit()
        if not self._refreshing:
            self._start_refresh(self._focused_probe_id)

    def _maybe_auto_log(self, report_key, title, content):
        if self.settings_engine.get_preference("auto_game_logbook", "false") != "true":
            return
        preference_key = f"auto_log_written:{self._focused_probe_id}:{report_key}"
        if self.settings_engine.get_preference(preference_key, "false") == "true":
            return
        try:
            self.service.create_logbook_page({"title": title[:120], "content": content[:20000]})
        except Exception as error:
            self._set_error("Automatic logbook report failed: " + (str(error) or type(error).__name__))
            return
        self.settings_engine.set_preference(preference_key, "true")

    @Slot(int, int, int, str, bool)
    def setAutonomousTravelTarget(self, x, y, z, route_mode, risk_acknowledged=False):
        if self.service is None:
            self._set_error("Refresh live account data before setting automation.")
            return
        try:
            store = DesiredStateStore(self.service.data_engine)
            current = store.load(self._focused_probe_id)
            state = DesiredState(
                production=current.production,
                resources=current.resources,
                fuel=current.fuel,
                inventory=current.inventory,
                repair=current.repair,
                maximum_mining_order_amount=current.maximum_mining_order_amount,
                maximum_safe_hop_distance=current.maximum_safe_hop_distance,
                travel=TravelGoal(
                    SectorCoordinates(x, y, z),
                    route_mode=str(route_mode or "segmented").strip().lower(),
                    risk_acknowledged=bool(risk_acknowledged),
                ),
                fleet=current.fleet,
            )
            store.save(state, self._focused_probe_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        automation["travelTarget"] = {
            "x": x,
            "y": y,
            "z": z,
            "routeMode": str(route_mode or "segmented").strip().lower(),
            "riskAcknowledged": bool(risk_acknowledged),
        }
        self._dashboard["automation"] = automation
        self._set_error("")
        self.dashboardChanged.emit()
        runtime = self._dashboard.get("automationRuntime", {})
        if (
            runtime.get("mode") == ExecutionMode.AUTOMATIC.value
            and runtime.get("liveExecutionEnabled")
            and "move_probe" in runtime.get("allowedCommandTypes", ())
        ):
            # A new travel goal is actionable immediately; do not require the
            # operator to wait for the next minute boundary or change focus.
            QTimer.singleShot(0, self._automation_tick)

    @Slot()
    def cancelAutonomousTravelTarget(self):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Refresh live account data before changing automation.")
            return
        try:
            store = DesiredStateStore(self.service.data_engine)
            current = store.load(self._focused_probe_id)
            state = DesiredState(
                production=current.production,
                resources=current.resources,
                fuel=current.fuel,
                inventory=current.inventory,
                repair=current.repair,
                maximum_mining_order_amount=current.maximum_mining_order_amount,
                maximum_safe_hop_distance=current.maximum_safe_hop_distance,
                travel=None,
                fleet=current.fleet,
            )
            store.save(state, self._focused_probe_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        automation["travelTarget"] = None
        self._dashboard["automation"] = automation
        self._set_error("")
        self.dashboardChanged.emit()

    @Slot("QVariantMap")
    def saveTransportCycle(self, value):
        if self.service is None:
            self._set_error("Refresh live account data before creating a transport cycle.")
            return
        try:
            operation = self.service.save_transport_cycle(self._qt_safe(value))
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        cycles = list(automation.get("transportCycles", ()))
        cycles.append(self._qt_safe(operation))
        automation["transportCycles"] = cycles
        self._dashboard["automation"] = automation
        self._set_error("")
        self.dashboardChanged.emit()

    @Slot(str)
    def startTransportCycle(self, operation_id):
        if self.service is None:
            self._set_error("Refresh live account data before starting a transport cycle.")
            return
        try:
            operation = self.service.start_transport_cycle(operation_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        automation["transportCycles"] = [
            self._qt_safe(operation) if item.get("id") == operation_id else item
            for item in automation.get("transportCycles", ())
        ]
        automation["travelTarget"] = operation["metadata"]["cycle"]["source"]
        self._dashboard["automation"] = automation
        self._set_error("")
        self.dashboardChanged.emit()
        runtime = self._dashboard.get("automationRuntime", {})
        if (
            runtime.get("mode") == ExecutionMode.AUTOMATIC.value
            and runtime.get("liveExecutionEnabled")
            and "move_probe" in runtime.get("allowedCommandTypes", ())
        ):
            self._automation_after_refresh = True
        self._start_refresh(self._focused_probe_id)

    @Slot(str)
    def deleteTransportCycle(self, operation_id):
        if self.service is None:
            self._set_error("Refresh live account data before removing a transport cycle.")
            return
        try:
            self.service.delete_transport_cycle(operation_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        automation["transportCycles"] = [
            item for item in automation.get("transportCycles", ())
            if item.get("id") != operation_id
        ]
        automation["travelTarget"] = DesiredStateStore(
            self.service.data_engine,
        ).load(self._focused_probe_id).to_dict().get("travelTarget")
        self._dashboard["automation"] = automation
        self._set_error("")
        self.dashboardChanged.emit()

    @Slot(str)
    def pauseTransportCycle(self, operation_id):
        if self.service is None:
            self._set_error(
                "Refresh live account data before pausing a transport route."
            )
            return
        try:
            operation = self.service.pause_transport_cycle(operation_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        automation["transportCycles"] = [
            self._qt_safe(operation) if item.get("id") == operation_id else item
            for item in automation.get("transportCycles", ())
        ]
        automation["travelTarget"] = None
        self._dashboard["automation"] = automation
        self._set_error("")
        self.dashboardChanged.emit()

    def _inventory_mutation(self, callback):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Refresh a focused probe before changing inventory.")
            return
        try:
            callback()
        except Exception as error:
            self._set_error(self._inventory_error_message(error))
            return
        self._set_error("")
        self._start_refresh(self._focused_probe_id)

    @staticmethod
    def _inventory_error_message(error):
        """Preserve public game business errors as useful operator guidance."""
        response = getattr(error, "response", None)
        payload = None
        if response is not None:
            try:
                payload = response.json()
            except (TypeError, ValueError):
                payload = None
        detail = payload.get("detail", payload) if isinstance(payload, dict) else {}
        business_error = detail.get("error", detail) if isinstance(detail, dict) else {}
        code = business_error.get("code") if isinstance(business_error, dict) else None
        message = business_error.get("message") if isinstance(business_error, dict) else None
        if code == "storage_container_reserved":
            return (
                "STORAGE CONTAINER RESERVED · An active crafting task has reserved "
                "space in this container for its output. Wait for or cancel that craft "
                "before detaching, dropping, transferring, or emptying the container."
            )
        if code == "invalid_cargo_reservation":
            return "INVALID CARGO RESERVATION · " + str(
                message or "The crafting output reservation became invalid and the Manny task was stopped."
            )
        if code or message:
            return " · ".join(str(value) for value in (code, message) if value)
        return str(error) or type(error).__name__

    @Slot(str)
    def renameFocusedProbe(self, name):
        if not name.strip():
            self._set_error("Probe name cannot be empty.")
            return
        self._inventory_mutation(lambda: self.service.rename_probe(name))

    @Slot(str, str)
    def renameStorageContainer(self, container_id, label):
        if not label.strip():
            self._set_error("Container label cannot be empty.")
            return
        self._inventory_mutation(lambda: self.service.rename_container(container_id, label))

    @Slot(str, str)
    def renameManny(self, manny_id, name):
        if not manny_id or not name.strip():
            self._set_error("Select a Manny and enter a non-empty name.")
            return
        self._inventory_mutation(lambda: self.service.rename_manny(manny_id, name))

    @Slot(str, "QVariantMap")
    def saveStorageRules(self, container_id, rules):
        self._inventory_mutation(
            lambda: self.service.update_container_rules(container_id, self._qt_safe(rules))
        )

    @Slot("QVariantMap")
    def moveStorage(self, payload):
        self._inventory_mutation(lambda: self.service.move_storage(self._qt_safe(payload)))

    @Slot(str, float, str)
    def jettisonInventory(self, item_id, amount, container_id):
        self._inventory_mutation(lambda: self.service.jettison_inventory(
            item_id,
            amount if amount > 0 else None,
            container_id or None,
        ))

    @Slot(str, str, "QVariantMap")
    def runInventoryMannyAction(self, action, manny_id, payload):
        self._inventory_mutation(lambda: self.service.inventory_manny_action(
            action, manny_id, self._qt_safe(payload),
        ))

    @Slot("QVariantMap")
    def sendMessage(self, payload):
        self._message_mutation(lambda: self.service.send_message(self._qt_safe(payload)))

    @Slot(str)
    def markMessageRead(self, message_id):
        self._message_mutation(lambda: self.service.mark_message_read(message_id))

    def _message_mutation(self, callback):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Refresh a focused probe before using communications.")
            return
        try:
            callback()
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._set_error("")
        self._start_refresh(self._focused_probe_id)

    @Slot(str, str)
    def createLogbookPage(self, title, content):
        payload = {"title": title, "content": content}
        self._logbook_mutation(
            lambda: self.service.create_logbook_page(payload),
            "create",
            payload=payload,
        )

    @Slot(int, str, str)
    def updateLogbookPage(self, page_id, title, content):
        payload = {"title": title, "content": content}
        self._logbook_mutation(
            lambda: self.service.update_logbook_page(page_id, payload),
            "update",
            page_id=page_id,
            payload=payload,
        )

    @Slot(int)
    def deleteLogbookPage(self, page_id):
        self._logbook_mutation(
            lambda: self.service.delete_logbook_page(page_id),
            "delete",
            page_id=page_id,
        )

    @Slot(int)
    def loadLogbookPage(self, page_id):
        if self.service is None:
            return
        try:
            page = self.service.get_logbook_page(page_id)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        logbook = dict(self._dashboard.get("logbook", {}))
        pages = [
            {**item, **self._qt_safe(page), "isNewDailyReport": False}
            if int(item.get("id", -1)) == page_id else item
            for item in logbook.get("pages", ())
        ]
        logbook["pages"] = pages
        logbook["newDailyReportCount"] = sum(
            1 for item in pages if item.get("isNewDailyReport")
        )
        self._dashboard["logbook"] = logbook
        self._set_error("")
        self.dashboardChanged.emit()

    def _logbook_mutation(self, callback, action, page_id=None, payload=None):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Refresh a focused probe before editing its logbook.")
            return
        try:
            response = callback()
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._set_error("")
        logbook = dict(self._dashboard.get("logbook", {}))
        pages = list(logbook.get("pages", ()))
        if action == "delete":
            pages = [item for item in pages if int(item.get("id", -1)) != int(page_id)]
        elif action == "update":
            pages = [
                {**item, **(payload or {})}
                if int(item.get("id", -1)) == int(page_id) else item
                for item in pages
            ]
        elif action == "create":
            page = response.get("page", response) if isinstance(response, dict) else {}
            if isinstance(page, dict) and page.get("id") is not None:
                item = {**(payload or {}), **page}
                item["sourceProbeId"] = self._focused_probe_id
                item["sourceProbeName"] = self._dashboard.get("focus", {}).get(
                    "name", f"Probe {self._focused_probe_id}"
                )
                pages.insert(0, item)
        logbook["pages"] = pages
        logbook["newDailyReportCount"] = sum(
            1 for item in pages if item.get("isNewDailyReport")
        )
        self._dashboard["logbook"] = logbook
        if hasattr(self.service, "_logbook_cache"):
            self.service._logbook_cache.pop(self._focused_probe_id, None)
        self.dashboardChanged.emit()

    @Slot(bool)
    def setAutoLogbookEnabled(self, enabled):
        self.settings_engine.set_preference("auto_game_logbook", "true" if enabled else "false")
        if self.service is not None:
            self.service.data_engine.set_preference("auto_game_logbook", "true" if enabled else "false")
        logbook = dict(self._dashboard.get("logbook", {}))
        logbook["autoLoggingEnabled"] = enabled
        self._dashboard["logbook"] = logbook
        self.dashboardChanged.emit()

    def _start_refresh(self, probe_id):
        if self._refreshing:
            return
        self._set_refreshing(True)
        self._set_error("")
        if self.service is None:
            try:
                self.service = MissionControlDataService()
            except Exception as error:
                self._set_error(str(error) or type(error).__name__)
                self._set_refreshing(False)
                return
        self._refresh_target_id = probe_id
        worker = _RefreshWorker(self.service, probe_id)
        worker.signals.succeeded.connect(self._accept_dashboard)
        worker.signals.failed.connect(self._reject_dashboard)
        worker.signals.progress.connect(self._set_loading_progress)
        self._worker = worker
        self.thread_pool.start(worker)

    @Slot(object)
    def _accept_dashboard(self, payload):
        if self._retry_timer.isActive():
            self._retry_timer.stop()
        self._retry_probe_id = None
        requested_probe_id = self._refresh_target_id
        previous_last_result = (
            self._dashboard.get("automationRuntime", {}).get("lastResult")
            if self._dashboard else None
        )
        payload["credentials"] = {
            "configured": self.credentialConfigured,
            "source": self.credentialSource,
            "message": self.credentialMessage,
        }
        payload = self._qt_safe(payload)
        self._dashboard = payload
        if previous_last_result is not None:
            runtime = dict(self._dashboard.get("automationRuntime", {}))
            runtime["lastResult"] = previous_last_result
            self._dashboard["automationRuntime"] = runtime
        self._api_compatible = True
        self._dashboard["compatibility"] = {
            "checked": True,
            "compatible": True,
            "serverVersion": payload.get("apiVersion"),
            "supportedMinimum": MINIMUM_API_VERSION,
            "supportedMaximum": MAXIMUM_API_VERSION,
            "checkIntervalHours": 6,
        }
        if not self._compatibility_timer.isActive():
            self._compatibility_timer.start()
        self._configure_automation_timer(payload.get("automationRuntime", {}))
        focused_runtime = payload.get("automationRuntime", {})
        if (
            self._initial_automation_cycle_pending
            and focused_runtime.get("mode") == ExecutionMode.AUTOMATIC.value
            and focused_runtime.get("liveExecutionEnabled")
        ):
            self._initial_automation_cycle_pending = False
            self._automation_after_refresh = True
        naming_policy = payload.get("automation", {}).get("namingPolicy", {})
        if (
            naming_policy.get("enabled")
            and payload.get("defaultProbeId") is not None
            and int(payload.get("focusedProbeId", self._focused_probe_id)) == int(payload["defaultProbeId"])
            and self._naming_worker is None
            and time.monotonic() - self._naming_last_audit >= 300
        ):
            self._naming_last_audit = time.monotonic()
            naming_worker = _FleetNamingWorker(naming_policy, False)
            naming_worker.signals.succeeded.connect(self._accept_fleet_naming_audit)
            naming_worker.signals.failed.connect(self._reject_fleet_naming)
            self._naming_worker = naming_worker
            self.thread_pool.start(naming_worker)
        emergency_stop = bool(payload.get("emergencyStopActive", False))
        if emergency_stop != self._emergency_stop:
            self._emergency_stop = emergency_stop
            self.emergencyStopChanged.emit()

        probes = [dict(item) for item in payload.get("probeOptions", ())]
        focus = dict(payload.get("focus", {}))
        focus_id = int(focus.get("probeId", -1))
        # Account-level probe rows currently omit some live telemetry. Retain
        # the last authoritative per-probe sector/status so a refresh or focus
        # change cannot turn every non-focused Fleet card into UNKNOWN.
        for item in probes:
            probe_id = int(item.get("id", -1))
            cached = self._probe_snapshot_cache.get(probe_id, {})
            if item.get("sectorLabel") in {None, "", "SECTOR UNKNOWN"}:
                item["sectorLabel"] = cached.get("sectorLabel", "SECTOR UNKNOWN")
            if item.get("status") in {None, "", "unknown"}:
                item["status"] = cached.get("status", "unknown")
            for telemetry_key, fallback in (
                ("movement", {}),
                ("velocity", 0),
                ("sensorMode", "unknown"),
                ("deuterium", 0),
                ("maxDeuterium", 100),
            ):
                telemetry_value = item.get(telemetry_key)
                if telemetry_value is None or telemetry_value == "" or (
                    isinstance(telemetry_value, str) and telemetry_value == "unknown"
                ) or (telemetry_key == "movement" and not telemetry_value):
                    item[telemetry_key] = cached.get(telemetry_key, fallback)
            if probe_id == focus_id:
                item["sectorLabel"] = focus.get("sectorLabel") or item.get("sectorLabel")
                item["status"] = focus.get("status") or item.get("status")
                item["model"] = focus.get("model") or item.get("model")
                for telemetry_key in (
                    "movement", "velocity", "sensorMode", "deuterium", "maxDeuterium",
                ):
                    if telemetry_key in focus:
                        item[telemetry_key] = focus[telemetry_key]
            self._probe_snapshot_cache[probe_id] = dict(item)
        # The account fleet endpoint may omit coordinates for non-focused
        # probes. Reconstruct same-sector transfer choices from the last
        # authoritative snapshot instead of presenting an empty selector.
        focused_row = self._probe_snapshot_cache.get(focus_id, {})
        focused_sector = focus.get("sectorLabel") or focused_row.get("sectorLabel")
        if focused_sector and focused_sector != "SECTOR UNKNOWN":
            peers = []
            for candidate_id, candidate in self._probe_snapshot_cache.items():
                if int(candidate_id) == focus_id:
                    continue
                if candidate.get("sectorLabel") != focused_sector:
                    continue
                peers.append({
                    "id": int(candidate_id),
                    "name": candidate.get("name", f"Probe {candidate_id}"),
                    "model": candidate.get("model", "generic"),
                    "fuel": float(candidate.get("deuterium", 0) or 0),
                    "maxFuel": float(candidate.get("maxDeuterium", 100) or 100),
                })
            if peers:
                inventory = dict(self._dashboard.get("inventoryManagement", {}))
                known_ids = {int(item.get("id", -1)) for item in inventory.get("sameSectorProbes", ())}
                inventory["sameSectorProbes"] = list(inventory.get("sameSectorProbes", ())) + [
                    item for item in peers if item["id"] not in known_ids
                ]
                self._dashboard["inventoryManagement"] = inventory
        if probes != self._available_probes:
            self._available_probes = probes
            self.availableProbesChanged.emit()

        probe_id = focus_id
        # A reconnect response for an older request must not steal focus from
        # the probe the operator explicitly selected while it was in flight.
        if requested_probe_id is not None and int(requested_probe_id) >= 0:
            probe_id = int(requested_probe_id) if any(
                int(item.get("id", -1)) == int(requested_probe_id) for item in probes
            ) else focus_id
        if probe_id != self._focused_probe_id:
            self._focused_probe_id = probe_id
            self.focusedProbeIdChanged.emit()
        self.dashboardChanged.emit()
        self._finish_refresh()

    @Slot(object)
    def _accept_fleet_naming_audit(self, result):
        self._naming_worker = None
        if int(result.get("renamedProbes", 0)) or int(result.get("renamedMannies", 0)):
            self._start_refresh(self._focused_probe_id if self._focused_probe_id >= 0 else None)

    @classmethod
    def _qt_safe(cls, value):
        """Convert nested Python containers into predictable QVariant shapes."""

        if isinstance(value, dict):
            return {str(key): cls._qt_safe(item) for key, item in value.items()}
        if isinstance(value, (tuple, list, set)):
            return [cls._qt_safe(item) for item in value]
        if hasattr(value, "keys") and not isinstance(value, (str, bytes)):
            return {str(key): cls._qt_safe(value[key]) for key in value.keys()}
        return value

    @Slot(str)
    def _reject_dashboard(self, message):
        message = message or "The game API did not return an error description."
        retry_probe_id = self._refresh_target_id
        retry_match = re.search(
            r"retry(?:\s+after|\s+in)?\s+(\d+(?:\.\d+)?)\s*seconds?",
            message,
            flags=re.IGNORECASE,
        )
        if retry_match:
            delay_seconds = max(1.0, float(retry_match.group(1)))
            self._retry_probe_id = retry_probe_id
            self._retry_timer.start(int(delay_seconds * 1000) + 250)
            message += f" Automatic retry scheduled in {delay_seconds:g} seconds."
        self._set_error(message)
        # A failed refresh must never replace live account data with UI concept
        # values. Keep the last authoritative snapshot, mark it stale, and let
        # QML explain that it is retained data rather than current telemetry.
        if self._dashboard:
            self._dashboard["connection"] = "stale"
            self._dashboard["connectionLabel"] = "LIVE LINK INTERRUPTED"
            self._dashboard["refreshError"] = message
            self.dashboardChanged.emit()
        self._automation_after_refresh = False
        self._finish_refresh()

    def _retry_rate_limited_refresh(self):
        probe_id = self._retry_probe_id
        self._retry_probe_id = None
        if not self._refreshing and self.credentialConfigured:
            self._start_refresh(probe_id)

    def _finish_refresh(self):
        self._set_startup_loading(False)
        self._worker = None
        self._refresh_target_id = None
        self._set_refreshing(False)
        pending = self._pending_probe_id
        self._pending_probe_id = None
        if pending is not None and pending != self._focused_probe_id:
            self._start_refresh(pending)
            return
        if self._automation_after_refresh:
            self._automation_after_refresh = False
            QTimer.singleShot(
                0,
                self._automation_tick,
            )

    def _set_refreshing(self, value):
        if value == self._refreshing:
            return
        self._refreshing = value
        self.refreshingChanged.emit()

    def _set_startup_loading(self, value):
        value = bool(value)
        if value == self._startup_loading:
            return
        self._startup_loading = value
        self.startupLoadingChanged.emit()

    @Slot(int, str)
    def _set_loading_progress(self, percent, status):
        self._loading_progress = max(0, min(100, int(percent)))
        self._loading_status = str(status)
        self.loadingProgressChanged.emit()

    def _set_error(self, value):
        if value == self._error:
            return
        if value:
            log_handled_error(value)
        self._error = value
        self.errorChanged.emit()
