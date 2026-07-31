"""Qt bridge and live read-only data loader for Mission Control."""

from __future__ import annotations

import traceback

import requests
from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, Signal, Slot

from src.api.capabilities import GameCapabilities
from src.api.client import GameClient
from src.application.hazard_context import HazardContextLoader
from src.application.history_sync import HistorySynchronizer
from src.application.probe_selector import ProbeSelector
from src.data import DataEngine
from src.intelligence.world_builder import WorldBuilder
from src.operations.operations import Operations
from src.presentation import MissionControlViewModelBuilder
from src.recipes.manager import RecipeManager
from src.safety.policy import TravelSafetyPolicyStore
from src.safety.resources import ResourceSafetyPolicyStore
from src.snapshot.manager import SnapshotManager


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
        dashboard = MissionControlViewModelBuilder(
            operations,
            self.data_engine,
        ).build()
        dashboard["apiVersion"] = self.api_version
        dashboard["player"] = self._player_view(player)
        dashboard["probeOptions"] = tuple(
            self._probe_option(item) for item in probe_data.get("probes", ())
        )
        dashboard["syncFailures"] = sync_failures
        return dashboard

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

    def __init__(self, service=None, thread_pool=None):
        super().__init__()
        self.service = service
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self._dashboard = {}
        self._available_probes = []
        self._focused_probe_id = -1
        self._refreshing = False
        self._error = ""
        self._worker = None

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

    @Slot()
    def refresh(self):
        self._start_refresh(self._focused_probe_id if self._focused_probe_id >= 0 else None)

    @Slot(int)
    def selectProbe(self, probe_id):
        if self._refreshing or probe_id == self._focused_probe_id:
            return
        self._start_refresh(probe_id)

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
        self._dashboard = dict(payload)
        self.dashboardChanged.emit()

        probes = [dict(item) for item in payload.get("probeOptions", ())]
        if probes != self._available_probes:
            self._available_probes = probes
            self.availableProbesChanged.emit()

        probe_id = int(payload.get("focus", {}).get("probeId", -1))
        if probe_id != self._focused_probe_id:
            self._focused_probe_id = probe_id
            self.focusedProbeIdChanged.emit()
        self._finish_refresh()

    @Slot(str)
    def _reject_dashboard(self, message):
        self._set_error(message)
        self._finish_refresh()

    def _finish_refresh(self):
        self._worker = None
        self._set_refreshing(False)

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
