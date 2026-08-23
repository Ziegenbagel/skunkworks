"""Capture the real Skunkworks QML with a synthetic documentation profile.

This tool never connects to the game API and never reads the operator's normal
or private-test database.  Its output is safe to use in public documentation.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QTimer, QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import DataEngine
from src.ui.app import configure_qt_plugin_paths
from src.ui.controller import MissionControlController


DEFAULT_OUTPUT = ROOT / "docs" / "user-guide" / "assets" / "screenshots"


class SyntheticCredentials:
    """Keep capture mode independent of the operating-system credential vault."""

    @staticmethod
    def get():
        return "synthetic-documentation-key"

    @staticmethod
    def source():
        return "synthetic documentation profile"


def synthetic_dashboard() -> dict:
    probes = [
        {"id": 1001, "name": "Wayfarer Hub", "model": "generic", "status": "arrived", "isReachable": True, "isDefault": True, "sectorLabel": "FCC 0 / 0 / 0"},
        {"id": 1002, "name": "Peregrine Explorer", "model": "generic", "status": "idle", "isReachable": True, "isDefault": False, "sectorLabel": "FCC 0 / 0 / 0"},
        {"id": 1003, "name": "Lantern Fuel Tender", "model": "deuterium_tanker", "status": "arrived", "isReachable": True, "isDefault": False, "sectorLabel": "FCC 1 / 1 / 0"},
        {"id": 1004, "name": "Harbor Fuel Reserve", "model": "deuterium_tanker", "status": "idle", "isReachable": True, "isDefault": False, "sectorLabel": "FCC 0 / 0 / 0"},
    ]
    neighbors = []
    for index, (x, y, z) in enumerate(((1, 1, 0), (1, -1, 0), (-1, 1, 0), (-1, -1, 0), (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1), (0, 1, 1), (0, 1, -1), (0, -1, 1), (0, -1, -1))):
        detailed = index in {1, 5, 8}
        neighbors.append({
            "x": x, "y": y, "z": z, "label": f"FCC {x} / {y} / {z}",
            "visited": detailed, "visitCount": 2 if detailed else 0,
            "knowledgeLevel": "detailed" if detailed else "neighbor_scan",
            "confidence": 1.0 if detailed else 0.55,
            "objectCount": 4 if detailed else 0,
            "scanSummary": "Quiet binary system with four orbital objects." if detailed else "No major nearby object estimated.",
            "detailText": "Synthetic documentation sector. No live account data.",
            "scutCoverage": {"covered": index < 7, "networkName": "DemoNet" if index < 7 else "", "relayId": 7000 + index if index < 7 else None},
        })
    mannies = [
        {"id": str(2000 + i), "name": f"WHub - {i:03d}", "currentTask": None}
        for i in range(1, 9)
    ]
    production = [
        {"id": "2001", "asset": "WHub - 001", "taskType": "crafting", "name": "Crafting Manny · 62%", "progress": 62, "eta": "18:24", "displayText": "WHUB - 001 · CRAFTING MANNY · 62%", "detailText": "Asset: WHub - 001\nOperation: Crafting\nRecipe: Manny\nAutomation reason: Maintain the configured Manny target."},
        {"id": "2002", "asset": "WHub - 002", "taskType": "mining", "name": "Mining metals · 31%", "progress": 31, "eta": "02:48:10", "displayText": "WHUB - 002 · MINING METALS · 31%", "detailText": "Asset: WHub - 002\nOperation: Mining\nTarget: Ferric Dawn\nTarget amount: 0.25 ECE\nDelivery: Attached storage"},
        {"id": "2003", "asset": "WHub - 003", "taskType": "mining", "name": "Mining ice · 78%", "progress": 78, "eta": "00:47:22", "displayText": "WHUB - 003 · MINING ICE · 78%", "detailText": "Asset: WHub - 003\nOperation: Mining\nTarget: Pale Comet\nTarget amount: 0.25 ECE"},
        {"id": "2004", "asset": "WHub - 004", "taskType": "idle", "name": "Idle · Ready", "progress": 0, "eta": "—", "displayText": "WHUB - 004 · IDLE · READY", "detailText": "Asset: WHub - 004\nStatus: Idle\nCan receive automation order: Yes"},
    ]
    inventory = {
        "probeId": 1001, "probeName": "Wayfarer Hub", "deuterium": 68.0, "maxDeuterium": 100.0,
        "containers": [
            {"id": 3001, "name": "General Stores", "capacity": 20.0, "usedCapacity": 12.4, "freeCapacity": 7.6},
            {"id": 3002, "name": "Metals Bay", "capacity": 20.0, "usedCapacity": 9.2, "freeCapacity": 10.8},
        ],
        "emptyAssemblyContainers": [{"id": 3010, "name": "Assembly Cradle A"}, {"id": 3011, "name": "Assembly Cradle B"}],
        "items": [{"id": 4001, "name": "SCUT Relay", "type": "scut_relay"}, {"id": 4002, "name": "SCUT Transit Beacon", "type": "scut_transit_beacon"}],
        "resourcePlacements": [{"resourceType": "metals", "containerId": 3002, "containerName": "Metals Bay", "amount": 9.2}],
        "idleMannies": mannies[3:], "mannies": mannies,
        "sameSectorProbes": probes[1:2],
        "sectorTargets": [{"id": 5001, "name": "Ferric Dawn"}, {"id": 5002, "name": "Pale Comet"}],
        "miningTargets": [{"id": 5001, "name": "Ferric Dawn", "resources": ["metals"]}, {"id": 5002, "name": "Pale Comet", "resources": ["ice", "carbon_compounds"]}],
        "detachedContainers": [{"id": 3020, "name": "Survey Cache"}], "recoverableObjects": [{"id": 3020, "name": "Survey Cache"}],
        "bookmarkTargets": [{"id": 5003, "name": "Blue Lantern"}], "inspectableObjects": [{"id": 5001, "name": "Ferric Dawn"}, {"id": 5002, "name": "Pale Comet"}],
        "inactiveScutRelays": [{"id": 6001, "name": "Relay Frame Seven"}], "activeScutRelaysWithoutBeacon": [{"id": 6002, "name": "DemoNet Relay"}],
        "refuelStations": [{"id": 6003, "name": "DemoNet Fuel Station"}],
        "motorizationTargets": [{"id": 5002, "name": "Pale Comet"}], "refuelAsteroidTargets": [], "launchableAsteroids": [], "sculptableAsteroids": [],
        "asteroidImpactTargets": [], "asteroidTrajectories": [], "asteroidMotorizationAvailable": False, "anatiformSculptingAvailable": False,
        "waitingCargoMannies": [],
    }
    return {
        "connection": "connected", "connectionLabel": "CONNECTED",
        "focus": {"probeId": 1001, "name": "Wayfarer Hub", "model": "generic", "status": "arrived", "isReachable": True, "sector": {"x": 0, "y": 0, "z": 0}, "sectorLabel": "FCC 0 / 0 / 0", "fuelPercent": 68.0, "movement": {}, "canCancelMovement": False},
        "probeOptions": probes,
        "fleet": {"total": 4, "idle": 2, "probes": probes, "statusCounts": {"idle": 2, "arrived": 2}, "readinessPercent": 100},
        "probe": {"fuelPercent": 68.0, "integrityPercent": 99.6, "inventoryFree": 42.6, "inventoryCapacity": 100.0, "inventoryUsed": 57.4, "mannyTotal": 8, "mannyAvailable": 5},
        "health": {"state": "ready", "readiness_percent": 100, "findings": [], "stateLabel": "READY", "summary": "No active threats detected"},
        "alerts": [{"id": 1, "number": 1042, "summary": "Synthetic training alert: storage inspection recommended"}],
        "resources": [
            {"type": "deuterium", "label": "DEUTERIUM", "reading": "68%  ·  68 / 100", "amount": 68.0, "capacity": 100.0, "value": 0.68},
            {"type": "metals", "label": "METALS", "reading": "9.20 ECE", "amount": 9.2, "capacity": 20.0, "value": 0.46},
            {"type": "ice", "label": "ICE", "reading": "12.75 ECE", "amount": 12.75, "capacity": 20.0, "value": 0.64},
            {"type": "carbon_compounds", "label": "CARBON COMPOUNDS", "reading": "11.40 ECE", "amount": 11.4, "capacity": 20.0, "value": 0.57},
        ],
        "sectorResources": [{"type": "metals", "label": "METALS", "amount": 840.0}, {"type": "ice", "label": "ICE", "amount": 1260.0}, {"type": "carbon_compounds", "label": "CARBON COMPOUNDS", "amount": 2140.0}, {"type": "deuterium", "label": "DEUTERIUM", "amount": 320.0}],
        "resourceLedger": {"rows": [], "notes": []}, "inventoryManagement": inventory,
        "sector": {"label": "FCC 0 / 0 / 0", "knowledgeLevel": "detailed", "confidence": 1.0, "objects": inventory["sectorTargets"], "system": {"name": "Wayfarer System", "planetCount": 4}, "activeMannies": production[:3], "blackHoleDanger": False, "emptyReason": ""},
        "galaxy": {"nodes": [{"x": n[0], "y": n[1], "z": n[2], "label": f"FCC {n[0]} / {n[1]} / {n[2]}", "knowledgeLevel": "detailed" if i % 3 == 0 else "scanned", "resources": {"metals": 1} if i % 4 == 0 else {}} for i, n in enumerate(((x, y, (x + y) % 3 - 1) for x in range(-5, 6) for y in range(-4, 5)))], "focusCoordinates": {"x": 0, "y": 0, "z": 0}, "focusProbeId": 1001, "edges": [], "sectorCount": 99, "unknownNeighborCount": 0, "recentTrail": [], "recentTrailNodes": [], "recentTrailCount": 0, "recentTrailProbeId": 1001, "scutRanges": [], "scutCoverageCells": [], "scutCoverageBoundary": []},
        "missions": [{"id": "demo-mission", "name": "Survey the Wayfarer Corridor", "status": "active", "description": "Synthetic documentation mission."}],
        "production": production, "events": [], "operations": [], "actions": [], "archive": [],
        "communications": {"inbox": [{"id": 1, "subject": "Welcome to the synthetic documentation fleet", "read": False}], "outbox": [], "unreadCount": 1},
        "navigation": {"current": {"x": 0, "y": 0, "z": 0, "label": "FCC 0 / 0 / 0", "isCurrent": True, "visited": True, "knowledgeLevel": "detailed", "confidence": 1.0, "objectCount": 4, "scanSummary": "Four planets around Wayfarer Star.", "detailText": "Synthetic documentation system with four planets.", "scutCoverage": {"covered": True, "networkName": "DemoNet", "relayId": 6002}}, "neighbors": neighbors, "travelReady": True, "fuelPercent": 68.0, "fuelAvailable": 68.0, "fuelCost": 2.0, "probeStatus": "arrived", "telemetryAvailable": True},
        "crafting": {
            "idleMannies": mannies[3:],
            "recipes": [
                {"id": "additional_container", "name": "Additional Container", "description": "Fold-out storage module.", "craftableBy": ["manny"], "durationSeconds": 180, "rawIngredients": [{"name": "Metals", "quantity": 0.54}]},
                {"id": "manny", "name": "Manny", "description": "Autonomous multipurpose maintenance unit.", "craftableBy": ["manny"], "durationSeconds": 86400, "rawIngredients": [{"name": "Metals", "quantity": 3.78}, {"name": "Carbon Compounds", "quantity": 0.9}, {"name": "Deuterium", "quantity": 0.86}]},
                {"id": "scut_relay", "name": "SCUT Relay", "description": "Local faster-than-light network relay.", "craftableBy": ["manny"], "durationSeconds": 21600, "rawIngredients": [{"name": "Metals", "quantity": 3.8}, {"name": "Ice", "quantity": 0.81}]},
            ],
            "probeAssemblies": [
                {"model": "generic", "name": "Generic Class Probe", "assemblyAvailable": True, "components": [{"quantity": 1, "name": "Deuterium Engine"}, {"quantity": 1, "name": "SCUT Relay"}, {"quantity": 5, "name": "Electric Motor"}, {"quantity": 2, "name": "Atomic Printer Part"}, {"quantity": 4, "name": "Solar Panel"}]},
                {"model": "deuterium_tanker", "name": "Tanker Class Probe", "assemblyAvailable": True, "components": [{"quantity": 1, "name": "Deuterium Engine"}, {"quantity": 2, "name": "Linear Actuator"}, {"quantity": 1, "name": "Integrated Circuit"}, {"quantity": 10, "name": "Steel Plate"}]},
            ],
        },
        "automation": {
            "fleetTargets": {"generic": 6, "deuterium_tanker": 3},
            "fleetPriorities": {"generic": 4, "deuterium_tanker": 3},
            "production": [{"recipeId": "manny", "name": "Manny", "quantity": 20, "priority": 2}, {"recipeId": "scut_relay", "name": "SCUT Relay", "quantity": 5, "priority": 3}],
            "resourceReserves": {"deuterium": 50, "metals": 8, "ice": 10, "carbon_compounds": 10},
            "resourcePriorities": {"deuterium": 3, "metals": 1, "ice": 1, "carbon_compounds": 1},
            "minimumFuelPercent": 20, "fuelPriority": 1, "minimumFreeCapacity": 15, "inventoryPriority": 2,
            "maximumMiningOrderAmount": 0.25, "maximumSafeHopDistance": 2,
            "repairTriggerPercent": 20, "repairTargetPercent": 100, "repairPriority": 2,
            "probeRoles": {"1001": "hub", "1002": "transport", "1003": "deuterium_tanker", "1004": "deuterium_reserve"},
            "probeRoleSettings": {
                "1002": {"resource": "metals", "loadingSector": {"x": 1, "y": 1, "z": 0}, "unloadingSector": {"x": 0, "y": 0, "z": 0}, "returnSector": {"x": 1, "y": 1, "z": 0}, "loadProbeId": 1001, "unloadProbeId": 1001, "loadPercent": 90, "unloadRemainingPercent": 10, "protectedDeuteriumPercent": 20, "contingencyHops": 1, "repeat": True},
                "1003": {"resource": "deuterium", "loadingSector": {"x": 1, "y": 1, "z": 0}, "unloadingSector": {"x": 0, "y": 0, "z": 0}, "returnSector": {"x": 1, "y": 1, "z": 0}, "loadProbeId": 1001, "unloadProbeId": 1001, "loadAmount": 400, "protectedDeuteriumPercent": 20, "contingencyHops": 1, "repeat": True},
                "1004": {"targetProbeId": 1001, "protectedDeuterium": 10},
            },
            "liveTargetStatus": [
                {"priority": 1, "category": "RESOURCE FLOOR", "label": "METALS", "statusText": "9.2 ECE onboard / 8 ECE minimum · target met", "met": True},
                {"priority": 2, "category": "PRODUCTION", "label": "MANNY", "statusText": "8 stored or active / 20 target · 12 remaining to produce", "met": False},
                {"priority": 3, "category": "FLEET", "label": "DEUTERIUM TANKER", "statusText": "2 current / 3 target · 1 remaining to assemble", "met": False},
            ],
            "namingPolicy": {"enabled": True, "pattern": "{probe}-M{number}", "sequenceStyle": "numeric", "digits": 3},
        },
        "automationRuntime": {"probeId": 1001, "mode": "automatic", "liveExecutionEnabled": True, "maxCommandsPerCycle": 5, "allowedCommandTypes": ["manny_craft", "atomic_printer_craft", "manny_assemble_probe", "manny_mine", "manny_repair"], "queue": [], "planning": [{"priority": 2, "action": "prepare manufacturing", "target": "manny", "reason": "The next unit is evaluated from total raw resources; assembly components remain reserved only for assembly.", "blockers": ["fabricator unavailable"]}, {"priority": 3, "action": "restore resource floor", "target": "ice", "reason": "Mine 0.25 ECE Ice from Pale Comet and deliver it to attached storage.", "blockers": ["no idle manny"]}], "emergencyStopActive": False},
        "credentials": {"configured": True, "source": "SYNTHETIC DOCUMENTATION PROFILE"},
        "defaultProbeId": 1001,
        "refreshDiagnostics": {"elapsedSeconds": 4.2, "stages": {"automation": 1.4, "focusedProbe": 0.6, "fleet": 0.5}},
        "logbook": {"pages": [{"id": "demo-report", "title": "Skunkworks Daily Report · 2026-08-20", "content": "SYNTHETIC DAILY OPERATIONS REPORT\nProbe: Wayfarer Hub\nRole: Hub\n\nCrafting orders dispatched: 3\nMining orders dispatched: 5\n\nGenerated from fictional documentation data.", "updatedAt": "2026-08-20T17:00:00Z"}], "autoLogEnabled": True},
        "blueprintSharing": {"networks": [{"id": 7001, "name": "DemoNet"}], "knownBlueprints": [], "recipientProbes": probes[1:]},
        "probeImprovements": [], "terminalRecovery": {},
    }


def capture(
    output: Path,
    workspace: str = "MISSION CONTROL",
    clicks: tuple[tuple[int, int], ...] = (),
    probe_id: int = 1001,
    scroll_y: int = 0,
    scroll_object: str = "",
    tab_object: str = "",
    tab_index: int = -1,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="skunkworks-doc-profile-") as temporary:
        engine_store = DataEngine(Path(temporary) / "synthetic.sqlite3")
        engine_store.set_preference("onboarding_complete", "true")
        controller = MissionControlController(settings_engine=engine_store, credential_store=SyntheticCredentials())
        controller._dashboard = synthetic_dashboard()
        controller._available_probes = list(controller._dashboard["probeOptions"])
        controller._focused_probe_id = probe_id
        for probe in controller._available_probes:
            if int(probe["id"]) == probe_id:
                controller._dashboard["focus"].update(probe)
                controller._dashboard["focus"]["probeId"] = probe_id
                controller._dashboard["automationRuntime"]["probeId"] = probe_id
                break
        controller._startup_loading = False

        configure_qt_plugin_paths()
        QQuickStyle.setStyle("Basic")
        app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
        qml_root = ROOT / "src" / "ui" / "qml"
        qml_engine = QQmlApplicationEngine()
        qml_engine.addImportPath(str(qml_root))
        qml_engine.load(QUrl.fromLocalFile(str(qml_root / "App.qml")))
        window = qml_engine.rootObjects()[0]
        window.setProperty("backend", controller)
        screen = window.findChild(object, "missionControlScreen")
        screen.setProperty("currentNavigation", workspace)

        def save_and_quit():
            if tab_object and tab_index >= 0:
                tab_bar = window.findChild(QObject, tab_object)
                if tab_bar is None:
                    raise RuntimeError(f"Could not find QML tab object {tab_object!r}")
                tab_bar.setProperty("currentIndex", tab_index)
                QTest.qWait(500)
            for x, y in clicks:
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(x, y))
                QTest.qWait(250)
            if scroll_y:
                target = window.findChild(QObject, scroll_object) if scroll_object else None
                if target is None:
                    candidates = []
                    for item in window.findChildren(QObject):
                        content_height = item.property("contentHeight")
                        height = item.property("height")
                        visible = item.property("visible")
                        if isinstance(content_height, (int, float)) and isinstance(height, (int, float)) and visible and content_height > height + 20:
                            candidates.append((content_height - height, item))
                    target = max(candidates, key=lambda pair: pair[0])[1] if candidates else None
                if target is not None:
                    content_item = target.property("contentItem")
                    if isinstance(content_item, QObject) and content_item.property("contentHeight") is not None:
                        target = content_item
                    target.setProperty("contentY", min(float(scroll_y), float(target.property("contentHeight")) - float(target.property("height"))))
                    QTest.qWait(250)
            image = window.grabWindow()
            if not image.save(str(output)):
                raise RuntimeError(f"Could not save {output}")
            app.quit()

        QTimer.singleShot(1200, save_and_quit)
        app.exec()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT / "mission-control.png")
    parser.add_argument("--workspace", default="MISSION CONTROL")
    parser.add_argument("--probe-id", type=int, default=1001)
    parser.add_argument("--scroll-y", type=int, default=0)
    parser.add_argument("--scroll-object", default="", help="QML objectName of the ScrollView/Flickable to position.")
    parser.add_argument("--tab-object", default="", help="QML objectName of a TabBar to select directly.")
    parser.add_argument("--tab-index", type=int, default=-1, help="Zero-based index for --tab-object.")
    parser.add_argument("--click", action="append", default=[], metavar="X,Y", help="Click a QML coordinate after opening the workspace; repeatable.")
    args = parser.parse_args()
    clicks = tuple(tuple(int(value) for value in item.split(",", 1)) for item in args.click)
    capture(args.output, args.workspace.upper(), clicks, args.probe_id, args.scroll_y, args.scroll_object, args.tab_object, args.tab_index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
