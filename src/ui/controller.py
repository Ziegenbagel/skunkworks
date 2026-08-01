"""Qt bridge and live read-only data loader for Mission Control."""

from __future__ import annotations

import traceback
import json
from dataclasses import asdict

import requests
from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, QTimer, Signal, Slot

from src.api.capabilities import GameCapabilities
from src.api.client import GameClient
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
from src.planner.desired_state import DesiredState
from src.planner.desired_state import TravelGoal
from src.planner.desired_state_store import DesiredStateStore
from src.models.galaxy import SectorCoordinates
from src.snapshot.manager import SnapshotManager
from src.security import CredentialStore
from src.planner.planner import Planner
from src.execution import (
    AutomationRuntime, CapabilityDispatcher, CommandPreparer,
    ExecutionMode, ExecutionPolicy,
)
from src.execution.policy import ExecutionPolicyStore


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

    def load(self, probe_id=None):
        self._initialize()
        player = self.client.get_player()
        probe_data = self.client.get_probes()
        selected = self.probe_selector.select(
            probe_data,
            arguments=[],
            preferred_probe_id=probe_id or self.data_engine.remembered_probe_id(),
        )
        self.data_engine.remember_probe(selected["id"])

        details = self.client.get_probe(selected["id"])
        probe = details.get("probe", details)
        mannies = None
        if selected.get("isReachable", True):
            mannies = self.client.get_mannies(selected["id"])

        world = self._build_world(player, probe_data, probe, selected, mannies)
        sync_failures = HistorySynchronizer(
            self.data_engine,
            self.capabilities,
        ).sync(
            world,
            selected["id"],
            reachable=selected.get("isReachable", True),
        )
        world.galaxy = self.data_engine.galaxy_map()
        world.hazard_context = HazardContextLoader(self.capabilities).load(
            world,
            selected["id"],
            reachable=selected.get("isReachable", True),
        )

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
        dashboard = MissionControlViewModelBuilder(
            operations,
            self.data_engine,
        ).build()
        dashboard["apiVersion"] = self.api_version
        dashboard["player"] = self._player_view(player)
        options = [self._probe_option(item) for item in probe_data.get("probes", ())]
        for option in options:
            if option["id"] == selected["id"]:
                option["sectorLabel"] = dashboard["focus"]["sectorLabel"]
                option["status"] = dashboard["focus"]["status"]
                option["model"] = dashboard["focus"]["model"]
        dashboard["probeOptions"] = options
        dashboard["syncFailures"] = sync_failures
        dashboard["emergencyStopActive"] = self.data_engine.emergency_stop_active()
        if self._last_scan_result is not None:
            dashboard.setdefault("navigation", {})["scanResult"] = self._last_scan_result
        desired_state = DesiredStateStore(self.data_engine).load()
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
        automation["transportCycles"] = [
            json.loads(row["payload_json"])
            for row in self.data_engine.operation_records()
            if json.loads(row["payload_json"]).get("metadata", {}).get("template") == "round_trip_transport"
        ]
        dashboard["automation"] = automation
        dashboard["automationRuntime"] = self.automation_view(operations, selected["id"])
        dashboard["logbook"] = self.logbook_view(selected["id"])
        return dashboard

    def logbook_view(self, probe_id=None):
        probe_id = probe_id or self._selected_probe_id
        summaries = self.capabilities.probes.logbook_pages(probe_id, limit=25).get("pages", ())
        return {
            "pages": list(summaries),
            "autoLoggingEnabled": self.data_engine.get_preference("auto_game_logbook", "false") == "true",
        }

    def get_logbook_page(self, page_id):
        response = self.capabilities.probes.get_logbook_page(self._selected_probe_id, page_id)
        return response.get("page", response)

    def create_logbook_page(self, payload):
        return self.capabilities.probes.create_logbook_page(self._selected_probe_id, payload)

    def update_logbook_page(self, page_id, payload):
        return self.capabilities.probes.update_logbook_page(self._selected_probe_id, page_id, payload)

    def delete_logbook_page(self, page_id):
        return self.capabilities.probes.delete_logbook_page(self._selected_probe_id, page_id)

    def automation_view(self, operations=None, probe_id=None):
        operations = operations or self._operations
        probe_id = probe_id or self._selected_probe_id
        policy = ExecutionPolicyStore().load()
        if operations is None or probe_id is None:
            self._prepared_commands = ()
        else:
            tasks = Planner(
                operations,
                DesiredStateStore(self.data_engine).load(),
            ).tasks()
            self._prepared_commands = CommandPreparer(
                operations, probe_id, policy,
            ).prepare(tasks)
        return {
            "mode": policy.mode.value,
            "liveExecutionEnabled": policy.live_execution_enabled,
            "allowedCommandTypes": [item.value for item in sorted(policy.allowed_command_types, key=lambda item: item.value)],
            "maxCommandsPerCycle": policy.max_commands_per_cycle,
            "queue": [self._prepared_view(item) for item in self._prepared_commands],
            "emergencyStopActive": self.data_engine.emergency_stop_active(),
        }

    @staticmethod
    def _prepared_view(prepared):
        command = prepared.command
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
        }

    def save_execution_policy(self, value):
        policy = ExecutionPolicy.from_dict(value)
        ExecutionPolicyStore().save(policy)
        return self.automation_view()

    def run_automation_cycle(self, fingerprint=None, risk_acknowledged=False):
        policy = ExecutionPolicyStore().load()
        self.automation_view()
        candidates = [
            item for item in self._prepared_commands
            if fingerprint is None or item.command.fingerprint == fingerprint
        ]
        if not candidates:
            return {"status": "idle", "message": "No actionable automation command is queued."}
        if policy.mode == ExecutionMode.OBSERVE:
            return {"status": "observe_only", "message": "Observe mode never sends commands."}
        if policy.mode == ExecutionMode.APPROVE and fingerprint is None:
            return {"status": "awaiting_approval", "message": "Select and approve a queued command."}
        if policy.mode == ExecutionMode.AUTOMATIC:
            candidates = [item for item in candidates if item.disposition == "ready"]
            if not candidates:
                return {
                    "status": "idle",
                    "message": "No allowlisted, unblocked command is ready for automatic execution.",
                }
        else:
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
        if result.status != "failed" or not isinstance(result.response, dict):
            return result.status.replace("_", " ").title()
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
        assessment = self._operations.travel_safety.assess(destination)
        if assessment is None:
            raise RuntimeError("Current sector is unavailable.")
        selected = next(
            (option for option in assessment.options if option.name == route_mode),
            assessment.recommended,
        )
        execution = selected.hops[0] if selected.hops else destination
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
        )
        operation = OperationFactory.create(
            "round_trip_transport",
            probe_id=plan.probe_id,
            metadata={"cycle": plan.to_dict()},
        )
        OperationStore(self.data_engine).save(operation)
        return operation.to_dict()

    def rename_probe(self, name):
        return self.capabilities.probes.update(self._selected_probe_id, name=name.strip())

    def rename_container(self, container_id, label):
        return self.capabilities.storage.update_container(
            self._selected_probe_id, container_id, {"label": label.strip()},
        )

    def update_container_rules(self, container_id, rules):
        return self.capabilities.storage.update_rules(
            self._selected_probe_id, container_id, rules,
        )

    def move_storage(self, payload):
        return self.capabilities.storage.move(self._selected_probe_id, payload)

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
            "status": probe.get("status", "unknown"),
            "sectorLabel": label,
            "isReachable": probe.get("isReachable", True),
            "isDefault": probe.get("isDefault", False),
        }


class _WorkerSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)


class _RefreshWorker(QRunnable):
    def __init__(self, service, probe_id):
        super().__init__()
        self.service = service
        self.probe_id = probe_id
        self.signals = _WorkerSignals()

    def run(self):
        try:
            payload = self.service.load(self.probe_id)
        except Exception as error:  # UI boundary: preserve the process and report.
            traceback.print_exc()
            self.signals.failed.emit(str(error) or type(error).__name__)
        else:
            self.signals.succeeded.emit(payload)


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

    def __init__(self, service=None, thread_pool=None, settings_engine=None, credential_store=None):
        super().__init__()
        self.service = service
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._dashboard = {}
        self._available_probes = []
        self._focused_probe_id = -1
        self._refreshing = False
        self._error = ""
        self._emergency_stop = False
        self._worker = None
        self._pending_probe_id = None
        self.settings_engine = settings_engine or (service.data_engine if service is not None and hasattr(service, "data_engine") else DataEngine())
        self.credential_store = credential_store or CredentialStore()
        self._credential_message = ""
        self._automation_timer = QTimer(self)
        self._automation_timer.setInterval(60_000)
        self._automation_timer.timeout.connect(self._automation_tick)

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
            return
        if not self.credentialConfigured:
            self._set_credential_message("Configure an API key in Settings.")
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

    @Slot()
    def runAutomationCycle(self):
        self._run_automation(None, False)

    @Slot(str, bool)
    def approveAutomationCommand(self, fingerprint, risk_acknowledged=False):
        self._run_automation(fingerprint, risk_acknowledged)

    def _run_automation(self, fingerprint, risk_acknowledged):
        if self.service is None or self._refreshing:
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
        if result.get("status") == "succeeded":
            self._start_refresh(self._focused_probe_id)

    def _automation_tick(self):
        runtime = self._dashboard.get("automationRuntime", {})
        if (
            runtime.get("mode") == "automatic"
            and runtime.get("liveExecutionEnabled")
            and not self._emergency_stop
        ):
            self._run_automation(None, False)

    def _configure_automation_timer(self, runtime):
        enabled = runtime.get("mode") == "automatic" and runtime.get("liveExecutionEnabled")
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
            DesiredStateStore(self.service.data_engine).save(state)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._dashboard["automation"] = self._qt_safe(state.to_dict())
        runtime = self.service.automation_view()
        self._dashboard["automationRuntime"] = self._qt_safe(runtime)
        self._configure_automation_timer(runtime)
        self._set_error("")
        self.dashboardChanged.emit()

    @Slot(int, str)
    def assignProbeRole(self, probe_id, role):
        if self.service is None:
            self.service = MissionControlDataService()
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

    @Slot(int, int, int)
    def setAutonomousTravelTarget(self, x, y, z):
        if self.service is None:
            self._set_error("Refresh live account data before setting automation.")
            return
        try:
            store = DesiredStateStore(self.service.data_engine)
            current = store.load()
            state = DesiredState(
                production=current.production,
                resources=current.resources,
                fuel=current.fuel,
                inventory=current.inventory,
                travel=TravelGoal(SectorCoordinates(x, y, z)),
                fleet=current.fleet,
            )
            store.save(state)
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        automation = dict(self._dashboard.get("automation", {}))
        automation["travelTarget"] = {"x": x, "y": y, "z": z}
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

    def _inventory_mutation(self, callback):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Refresh a focused probe before changing inventory.")
            return
        try:
            callback()
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._set_error("")
        self._start_refresh(self._focused_probe_id)

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

    @Slot(str, "QVariantMap")
    def saveStorageRules(self, container_id, rules):
        self._inventory_mutation(
            lambda: self.service.update_container_rules(container_id, self._qt_safe(rules))
        )

    @Slot("QVariantMap")
    def moveStorage(self, payload):
        self._inventory_mutation(lambda: self.service.move_storage(self._qt_safe(payload)))

    @Slot(str, str)
    def createLogbookPage(self, title, content):
        self._logbook_mutation(lambda: self.service.create_logbook_page({"title": title, "content": content}))

    @Slot(int, str, str)
    def updateLogbookPage(self, page_id, title, content):
        self._logbook_mutation(lambda: self.service.update_logbook_page(page_id, {"title": title, "content": content}))

    @Slot(int)
    def deleteLogbookPage(self, page_id):
        self._logbook_mutation(lambda: self.service.delete_logbook_page(page_id))

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
            {**item, **self._qt_safe(page)} if int(item.get("id", -1)) == page_id else item
            for item in logbook.get("pages", ())
        ]
        logbook["pages"] = pages
        self._dashboard["logbook"] = logbook
        self._set_error("")
        self.dashboardChanged.emit()

    def _logbook_mutation(self, callback):
        if self.service is None or self._focused_probe_id < 0:
            self._set_error("Refresh a focused probe before editing its logbook.")
            return
        try:
            callback()
        except Exception as error:
            self._set_error(str(error) or type(error).__name__)
            return
        self._set_error("")
        self._start_refresh(self._focused_probe_id)

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
        worker = _RefreshWorker(self.service, probe_id)
        worker.signals.succeeded.connect(self._accept_dashboard)
        worker.signals.failed.connect(self._reject_dashboard)
        self._worker = worker
        self.thread_pool.start(worker)

    @Slot(object)
    def _accept_dashboard(self, payload):
        payload["credentials"] = {
            "configured": self.credentialConfigured,
            "source": self.credentialSource,
            "message": self.credentialMessage,
        }
        payload = self._qt_safe(payload)
        self._dashboard = payload
        self._configure_automation_timer(payload.get("automationRuntime", {}))
        self.dashboardChanged.emit()

        emergency_stop = bool(payload.get("emergencyStopActive", False))
        if emergency_stop != self._emergency_stop:
            self._emergency_stop = emergency_stop
            self.emergencyStopChanged.emit()

        probes = [dict(item) for item in payload.get("probeOptions", ())]
        if probes != self._available_probes:
            self._available_probes = probes
            self.availableProbesChanged.emit()

        probe_id = int(payload.get("focus", {}).get("probeId", -1))
        if probe_id != self._focused_probe_id:
            self._focused_probe_id = probe_id
            self.focusedProbeIdChanged.emit()
        self._finish_refresh()

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
        self._set_error(message)
        self._finish_refresh()

    def _finish_refresh(self):
        self._worker = None
        self._set_refreshing(False)
        pending = self._pending_probe_id
        self._pending_probe_id = None
        if pending is not None and pending != self._focused_probe_id:
            self._start_refresh(pending)

    def _set_refreshing(self, value):
        if value == self._refreshing:
            return
        self._refreshing = value
        self.refreshingChanged.emit()

    def _set_error(self, value):
        if value == self._error:
            return
        self._error = value
        self.errorChanged.emit()
