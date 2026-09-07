"""Stable UI view model assembled only from application services."""

from dataclasses import asdict
from datetime import datetime
import hashlib
import json
import re
from collections import Counter, defaultdict
from src.models.galaxy import SectorCoordinates
from src.data.engine import DataEngine


class MissionControlViewModelBuilder:
    """Keep future widgets isolated from the World Model and API payloads."""

    def __init__(self, operations, data_engine=None):
        self.operations = operations
        self.data_engine = data_engine

    def build(self):
        world = self.operations.world
        probe = world.probe
        fleet = getattr(world, "fleet", None) or {
            "total": 1, "idle": int(probe.get("status") == "idle"),
            "probes": (probe,),
        }
        health = self.operations.health.assess()
        coordinates = self._coordinates(probe, world.sector)
        findings = tuple(asdict(item) for item in health.findings)
        connection = self._connection_state(probe, world.snapshot)
        health_view = asdict(health)
        health_view["stateLabel"] = health.state.upper()
        health_view["summary"] = findings[0]["summary"] if findings else "No active threats detected"
        result = {
            "connection": connection,
            "connectionLabel": connection.replace("_", " ").upper(),
            "focus": {
                "probeId": probe["id"],
                "name": probe.get("name", world.snapshot.get("probe", f"Probe {probe['id']}")),
                "model": probe.get("model", "generic"),
                "status": (probe.get("movement") or {}).get("phase") or (probe.get("movement") or {}).get("status") or probe["status"],
                "isReachable": probe.get("telemetry_available", True),
                "sector": coordinates,
                "sectorLabel": self._sector_label(coordinates),
                "movement": self._movement_view(probe),
                "sensorMode": probe.get("sensor_mode", probe.get("sensorMode", "unknown")),
                "velocity": probe.get("velocity", (probe.get("movement") or {}).get("velocity")),
                "fuelPercent": self.operations.travel.fuel_percentage(),
                "canCancelMovement": (
                    (probe.get("movement") or {}).get("phase") == "preparing"
                    or (probe.get("movement") or {}).get("status") == "preparing"
                ),
            },
            "fleet": {
                "total": fleet.get("total", len(fleet.get("probes", ()))),
                "idle": fleet.get("idle", 0),
                "probes": tuple(fleet.get("probes", ())),
                "statusCounts": dict(fleet.get("status_counts", {})),
                "readinessPercent": health.readiness_percent,
            },
            "probe": {
                "fuelPercent": self.operations.travel.fuel_percentage(),
                "integrityPercent": float(probe.get("systems", {}).get("integrityPercent", 100)),
                "inventoryFree": self.operations.inventory.free_capacity(),
                "inventoryCapacity": float((probe.get("inventory") or {}).get("capacity", 0) or 0),
                "inventoryUsed": max(0, float((probe.get("inventory") or {}).get("capacity", 0) or 0) - self.operations.inventory.free_capacity()),
                "mannyTotal": self.operations.mannies.total(),
                "mannyAvailable": len(self.operations.mannies.available()),
            },
            "depots": tuple(asdict(depot) for depot in self.operations.depots.all()),
            "health": health_view,
            "alerts": self._dashboard_alerts(findings),
            "resources": self._resources(probe),
            "resourceLedger": self._resource_ledger(world),
            "inventoryManagement": self._inventory_management(world),
            "sector": self._sector_view(world, coordinates),
            "galaxy": self._galaxy_view(world, coordinates),
            "missions": self._missions(),
            "production": self._production(
                probe,
                world.mannies,
                self._automation_task_reasons(world.mannies, probe.get("id")),
            ),
            "events": self.operations.events.timeline(probe["id"])
                if self.operations.events else (),
            "operations": self._operation_records(),
            "actions": self._action_records(),
            "archive": self._archive_records(),
            "communications": self._communications(probe),
        }
        result["reports"] = self._reports(
            result["archive"], result["actions"], result["operations"],
        )
        result["navigation"] = self.navigation_view()
        result["sectorResources"] = self._sector_resource_totals(
            result["resourceLedger"], source_type="asteroid",
        )
        result["planetaryResources"] = self._sector_resource_totals(
            result["resourceLedger"], source_type="planet",
        )
        return result

    @staticmethod
    def _sector_resource_totals(ledger, source_type=None):
        totals = {"deuterium": 0.0, "metals": 0.0, "ice": 0.0, "carbon_compounds": 0.0}
        for row in ledger.get("rows", ()):
            if row.get("scope") != "natural_deposit":
                continue
            if source_type is not None and row.get("sourceType") != source_type:
                continue
            for resource_type, amount in (row.get("resources") or {}).items():
                key = MissionControlViewModelBuilder._normalized_resource_type(resource_type)
                if key in totals:
                    totals[key] += float(amount or 0)
        return tuple({"type": key, "label": key.replace("_", " ").upper(), "amount": amount} for key, amount in totals.items())

    @staticmethod
    def _inventory_management(world):
        inventory = world.probe.get("inventory", {})
        probe_name = world.probe.get("name", "Probe")
        containers = tuple(
            MissionControlViewModelBuilder._normalized_container(container, probe_name)
            for container in (inventory.get("containers", ()) or ())
        )
        items = []
        for item in inventory.get("items", ()) or ():
            container = item.get("container") or {}
            items.append({
                "id": str(item.get("id", "")),
                "type": item.get("type", "unknown"),
                "name": item.get("name") or str(item.get("type", "Unknown")).replace("_", " ").title(),
                "containerId": container.get("id", "unknown"),
                "containerLabel": MissionControlViewModelBuilder._container_label(container, probe_name),
                "containerSpace": float(item.get("containerSpace", 0) or 0),
                "currentTask": item.get("currentTask"),
                "canJettison": bool(item.get("canJettison", item.get("type") not in {"additional_container", "deuterium_tank"})),
            })
        resource_lines = []
        for stock in inventory.get("resourceStocks", ()) or ():
            for placement in stock.get("containers", ()) or ():
                container = placement.get("container") or {}
                resource_lines.append({
                    "id": str(stock.get("id") or f"probe-{world.probe.get('id')}-stock-{str(stock.get('type')).replace('_', '-')}"),
                    "resourceType": stock.get("type"),
                    "name": stock.get("name") or str(stock.get("type", "resource")).replace("_", " ").title(),
                    "containerId": container.get("id"),
                    "containerLabel": MissionControlViewModelBuilder._container_label(container, probe_name),
                    "amount": float(placement.get("amount", 0) or 0),
                    "displayText": f"{stock.get('name') or str(stock.get('type', 'resource')).replace('_', ' ').title()} · {MissionControlViewModelBuilder._container_label(container, probe_name)} · {float(placement.get('amount', 0) or 0):g} ECE",
                })
        idle_mannies = tuple({
            "id": str(manny.get("id")),
            "name": manny.get("name", "Manny"),
        } for manny in (world.mannies or {}).get("mannies", ())
            if manny.get("currentTask") is None and manny.get("canReceiveOrders", False))
        all_mannies = tuple({
            "id": str(manny.get("id")),
            "name": manny.get("name", "Manny"),
            "currentTask": manny.get("currentTask"),
        } for manny in (world.mannies or {}).get("mannies", ()))

        current_sector = world.probe.get("sector") or {}
        current_coordinates = current_sector.get("relative") or current_sector.get("relativeCoordinates") or {}
        same_sector_probes = []
        for candidate in (getattr(world, "fleet", None) or {}).get("probes", ()):
            if candidate.get("id") == world.probe.get("id"):
                continue
            candidate_sector = candidate.get("sector") or {}
            coordinates = candidate_sector.get("relative") or candidate_sector.get("relativeCoordinates") or {}
            if current_coordinates and coordinates == current_coordinates:
                same_sector_probes.append({
                    "id": int(candidate["id"]),
                    "name": candidate.get("name", f"Probe {candidate['id']}"),
                    "model": candidate.get("model", "generic"),
                    "fuel": float((candidate.get("fuel") or {}).get("deuterium", 0) or 0),
                    "maxFuel": float((candidate.get("fuel") or {}).get("maxDeuterium", 100) or 100),
                })

        sector_targets = []
        mining_targets = []
        recoverable_objects = []
        bookmark_targets = []
        inspectable_objects = []
        inactive_scut_relays = []
        active_scut_relays = []
        refuel_stations = []
        motorization_targets = []
        refuel_asteroid_targets = []
        launchable_asteroids = []
        sculptable_asteroids = []
        impact_targets = []
        missile_targets = []
        moving_missiles = []
        asteroid_trajectories = []
        seen_targets = set()
        seen_recoverable = set()
        seen_bookmarks = set()
        seen_inspectable = set()
        snapshot = (world.sector.get("snapshot") or {}).get("sector", {})
        def collect_targets(values, *, bookmark_candidates=False):
            for value in values or ():
                target_type = re.sub(
                    r"([a-z0-9])([A-Z])", r"\1_\2", str(value.get("type", ""))
                ).strip().lower().replace("-", "_").replace(" ", "_")
                if MissionControlViewModelBuilder._is_others_mothership_wreck(
                    value, target_type,
                ):
                    target_type = "others_mothership_wreck"
                elif str(value.get("observedClass", "")).casefold() in {
                    "large_ship", "ship",
                }:
                    target_type = "others_ship"
                target_kind = "planet" if "planet" in target_type else "asteroid" if "asteroid" in target_type else ""
                if not target_kind and value.get("mannyMineable", False):
                    target_kind = target_type or "mineable_object"
                target_id = str(value.get("id", ""))
                if target_id and target_type in {"star", "planet", "asteroid", "probe"}:
                    impact_targets.append({
                        "id": target_id,
                        "name": value.get("name") or value.get("summary") or target_id,
                        "label": (
                            f"{value.get('name') or value.get('summary') or target_id}"
                            f" · {target_type.replace('_', ' ').upper()}"
                        ),
                        "type": target_type,
                    })
                combat_target_type = (
                    "motorized_asteroid"
                    if target_type == "asteroid" and value.get("motorized", False)
                    else target_type
                )
                if target_id and combat_target_type in {
                    "probe", "manny", "missile", "others_ship",
                    "others_auxiliary", "motorized_asteroid",
                }:
                    missile_targets.append({
                        "id": target_id,
                        "name": value.get("name") or value.get("summary") or target_id,
                        "type": combat_target_type,
                        "label": f"{value.get('name') or value.get('summary') or target_id} · {combat_target_type.replace('_', ' ').upper()}",
                    })
                if target_type == "missile" and target_id:
                    moving_missiles.append({
                        "id": target_id,
                        "name": value.get("name") or target_id,
                        "launcherKind": value.get("launcherKind", "unknown"),
                        "targetKind": value.get("targetKind", "unknown"),
                        "targetId": str(value.get("targetId", "")),
                        "launchedAt": value.get("launchedAt"),
                        "impactAt": value.get("impactAt"),
                        "impactEpochMs": MissionControlViewModelBuilder._iso_epoch_ms(value.get("impactAt")),
                        "targetsCurrentProbe": bool(value.get("targetsCurrentProbe", False)),
                    })
                if target_type == "asteroid" and target_id:
                    asteroid = {
                        "id": target_id,
                        "name": value.get("name") or value.get("summary") or target_id,
                        "motorized": bool(value.get("motorized", False)),
                        "motorFuelStatus": value.get("motorFuelStatus"),
                        "trajectory": value.get("trajectory"),
                        "distinctiveFeature": value.get("distinctiveFeature"),
                    }
                    if not asteroid["distinctiveFeature"]:
                        sculptable_asteroids.append(asteroid)
                    if not asteroid["motorized"]:
                        motorization_targets.append(asteroid)
                    elif asteroid["trajectory"]:
                        asteroid_trajectories.append(asteroid["trajectory"])
                    elif asteroid["motorFuelStatus"] == "empty":
                        refuel_asteroid_targets.append(asteroid)
                    elif asteroid["motorFuelStatus"] == "full":
                        launchable_asteroids.append(asteroid)
                if target_kind and target_id and target_id not in seen_targets:
                    seen_targets.add(target_id)
                    sector_targets.append({
                        "id": target_id,
                        "name": value.get("name") or value.get("summary") or value.get("id", "Target"),
                        "type": target_kind,
                    })
                    resource_types = value.get("resourceTypes") or tuple(
                        key for key, amount in (value.get("resourceAmounts") or {}).items()
                        if float(amount or 0) > 0
                    )
                    if value.get("mannyMineable", target_kind == "asteroid") and resource_types:
                        mining_targets.append({
                            "id": target_id,
                            "name": value.get("name") or value.get("summary") or target_id,
                            "type": target_kind,
                            "resourceTypes": tuple(resource_types),
                        })
                is_container = "container" in target_type
                is_recoverable = value.get("recoverable") or value.get("salvageable") or (
                    is_container and value.get("mode") in {"drifting", "hidden_on_asteroid"}
                )
                if is_recoverable and target_id and target_id not in seen_recoverable:
                    seen_recoverable.add(target_id)
                    recoverable_objects.append({
                        "id": target_id,
                        "name": value.get("name") or value.get("summary") or target_id,
                        "type": target_type or "object",
                        "mode": value.get("mode", "drifting"),
                        "targetObjectId": value.get("targetObjectId"),
                        "capacity": float(value.get("capacity", 0) or 0),
                        "freeCapacity": float(value.get("freeCapacity", value.get("capacity", 0)) or 0),
                        "rules": value.get("rules") or {},
                    })
                if bookmark_candidates and target_id and target_id not in seen_bookmarks:
                    seen_bookmarks.add(target_id)
                    bookmark_targets.append({
                        "id": target_id,
                        "name": value.get("name") or value.get("summary") or f"{target_type.replace('_', ' ').title()} · {target_id}",
                        "type": target_type or "celestial_object",
                    })
                if target_type in {
                    "planet", "asteroid", "detached_container",
                    "dormant_construct", "others_mothership_wreck",
                } and target_id and target_id not in seen_inspectable:
                    seen_inspectable.add(target_id)
                    inspectable_objects.append({
                        "id": target_id,
                        "name": value.get("name") or value.get("summary") or f"{target_type.replace('_', ' ').title()} · {target_id}",
                        "type": target_type,
                    })
                if target_type == "scut_relay" and target_id:
                    relay = {
                        "id": target_id,
                        "name": value.get("name") or f"SCUT Relay {target_id}",
                        "status": str(value.get("status", "off")).lower(),
                        "hasTransitBeacon": bool(value.get("isTransitBeacon", value.get("hasTransitBeacon", False))),
                    }
                    if relay["status"] == "on":
                        if not relay["hasTransitBeacon"]:
                            active_scut_relays.append(relay)
                    else:
                        inactive_scut_relays.append(relay)
                if target_type == "deuterium_refuel_station" and target_id:
                    refuel_stations.append({
                        "id": target_id,
                        "name": value.get("name") or value.get("summary") or f"Deuterium Station · {target_id}",
                    })
                collect_targets(value.get("objects"))
                collect_targets(value.get("minableTargets"))
                collect_targets(value.get("bookmarkTargets"), bookmark_candidates=True)
        collect_targets(snapshot.get("objects"))
        collect_targets(snapshot.get("minableTargets"))
        for candidate in snapshot.get("probes", ()) or ():
            if candidate.get("owned", False) or not candidate.get("id"):
                continue
            candidate_name = candidate.get("name") or f"Probe {candidate['id']}"
            missile_targets.append({
                "id": str(candidate["id"]),
                "name": candidate_name,
                "type": "probe",
                "label": f"{candidate_name} · PROBE",
            })
        detached = tuple(item for item in recoverable_objects if "container" in item["type"])
        missile_items = tuple(
            item for item in items if str(item.get("type", "")).casefold() == "missile"
        )
        result = {
            "probeId": world.probe.get("id"),
            "probeName": world.probe.get("name", "Probe"),
            "containers": containers,
            "emptyAssemblyContainers": tuple(
                container for container in containers
                if (
                    (container.get("kind") == "container" or container.get("type") == "additional_container")
                    and float(container.get("usedCapacity", 0) or 0) <= 0
                )
            ),
            "items": tuple(items),
            "resourcePlacements": tuple(resource_lines),
            "idleMannies": idle_mannies,
            "mannies": all_mannies,
            "sameSectorProbes": tuple(same_sector_probes),
            "sectorTargets": tuple(sector_targets),
            "miningTargets": tuple(mining_targets),
            "detachedContainers": tuple(detached),
            "recoverableObjects": tuple(recoverable_objects),
            "bookmarkTargets": tuple(bookmark_targets),
            "inspectableObjects": tuple(inspectable_objects),
            "inactiveScutRelays": tuple(inactive_scut_relays),
            "activeScutRelaysWithoutBeacon": tuple(active_scut_relays),
            "refuelStations": tuple(refuel_stations),
            "motorizationTargets": tuple({item["id"]: item for item in motorization_targets}.values()),
            "refuelAsteroidTargets": tuple({item["id"]: item for item in refuel_asteroid_targets}.values()),
            "launchableAsteroids": tuple({item["id"]: item for item in launchable_asteroids}.values()),
            "sculptableAsteroids": tuple({item["id"]: item for item in sculptable_asteroids}.values()),
            "asteroidImpactTargets": tuple({item["id"]: item for item in impact_targets}.values()),
            "asteroidTrajectories": tuple({item.get("id"): item for item in asteroid_trajectories if item}.values()),
            "missileItems": missile_items,
            "missileTargets": tuple({item["id"]: item for item in missile_targets}.values()),
            "movingMissiles": tuple({item["id"]: item for item in moving_missiles}.values()),
            "targetedMissiles": tuple(item for item in moving_missiles if item["targetsCurrentProbe"]),
            "asteroidMotorizationAvailable": any(
                improvement.get("id") == "distributed_thrust_anchoring"
                and improvement.get("available", False)
                for improvement in (
                    ((getattr(world, "hazard_context", None) or {}).get("improvements") or {}).get("improvements", ())
                )
            ),
            "anatiformSculptingAvailable": any(
                improvement.get("id") == "anatiform_asteroid_sculpting"
                and improvement.get("available", False)
                for improvement in (
                    ((getattr(world, "hazard_context", None) or {}).get("improvements") or {}).get("improvements", ())
                )
            ),
            "waitingCargoMannies": tuple(
                manny for manny in all_mannies
                if (
                    (manny.get("currentTask") or {}).get("type")
                    if isinstance(manny.get("currentTask"), dict)
                    else manny.get("currentTask")
                ) == "waiting_for_space"
            ),
            "deuterium": float((world.probe.get("fuel") or {}).get("deuterium", world.probe.get("deuterium", 0)) or 0),
            "maxDeuterium": float((world.probe.get("fuel") or {}).get("maxDeuterium", 100) or 100),
        }
        return result

    @staticmethod
    def _container_label(container, probe_name):
        label = str(container.get("label") or "").strip()
        if container.get("kind") == "probe" or container.get("id") == "probe-core" or label.casefold() == "sonde":
            return f"Probe · {probe_name}"
        return label or "Unknown container"

    @classmethod
    def _normalized_container(cls, container, probe_name):
        result = dict(container)
        result["label"] = cls._container_label(container, probe_name)
        return result

    @classmethod
    def _resource_ledger(cls, world):
        rows = []
        inventory = world.probe.get("inventory", {})
        probe_name = world.probe.get("name", f"Probe {world.probe.get('id', '?')}")

        for stock in inventory.get("resourceStocks", ()):
            placements = stock.get("containers", ()) or ()
            if not placements:
                rows.append(cls._resource_row(
                    "probe_storage", probe_name, stock.get("type"), stock.get("amount", 0),
                    "Probe inventory · container placement unavailable",
                ))
            for placement in placements:
                container = placement.get("container", {})
                rows.append(cls._resource_row(
                    "probe_storage",
                    container.get("label") or container.get("id") or probe_name,
                    stock.get("type"), placement.get("amount", 0),
                    "Probe storage container" if container.get("kind") == "container" else "Probe core storage",
                ))

        fuel = world.probe.get("fuel", {})
        if fuel.get("deuterium") is not None:
            rows.append(cls._resource_row(
                "probe_storage", probe_name, "deuterium", fuel.get("deuterium", 0),
                "Probe fuel reserve", unit="%",
            ))

        for target in world.sector.get("resources", ()):
            amounts = {
                resource_type: float(amount or 0)
                for resource_type, amount in (target.get("resources") or {}).items()
                if float(amount or 0) > 0
            }
            reserve_lines = [
                f"{resource_type.replace('_', ' ').title()}: {amount:g} ECE"
                for resource_type, amount in amounts.items()
            ]
            rows.append({
                "scope": "natural_deposit",
                "objectId": str(target.get("id", "")),
                "title": target.get("name") or target.get("id", "Mineable object"),
                "detail": "\n".join(reserve_lines) if reserve_lines else "No remaining mineable resources",
                "sourceType": target.get("type", "mineable_object"),
                "classification": target.get("classification", "observed"),
                "resources": amounts,
                "harvestedByOthers": bool(target.get("harvestedByOthers", False)),
                "requiresAutomationApproval": bool(target.get("requiresAutomationApproval", False)),
                "automationApproved": bool(target.get("automationApproved", False)),
            })

        snapshot = world.sector.get("snapshot") or {}
        objects = (snapshot.get("sector") or {}).get("objects", ()) or ()
        for object_ in objects:
            cls._append_container_rows(rows, object_)
            for container in object_.get("storageContainers", ()) or ():
                nested = dict(container)
                nested.setdefault("targetObjectId", object_.get("id"))
                nested.setdefault("targetObjectName", object_.get("name"))
                cls._append_container_rows(rows, nested, force=True)

        return {
            "rows": tuple(rows),
            "notes": (
                "Planet-dropped containers are retained by the game but are not exposed by current sector observation endpoints.",
                "Detached-container contents are hidden by the API; visible entries show location and capacity until recovered.",
            ),
        }

    @classmethod
    def _append_container_rows(cls, rows, object_, force=False):
        type_ = str(object_.get("type") or object_.get("kind") or "").lower()
        if not force and "container" not in type_:
            return
        mode = object_.get("mode") or ("attached_to_object" if object_.get("targetObjectId") else "drifting")
        target = object_.get("targetObjectName") or object_.get("targetObjectId")
        location = "Floating in sector" if mode == "drifting" else f"Placed on {target or 'sector object'}"
        stocks = object_.get("resourceStocks") or (object_.get("inventory") or {}).get("resourceStocks") or ()
        if stocks:
            for stock in stocks:
                rows.append(cls._resource_row(
                    "detached_container", object_.get("name") or object_.get("id", "Detached container"),
                    stock.get("type"), stock.get("amount", 0), location,
                ))
        else:
            rows.append({
                "scope": "detached_container",
                "title": object_.get("name") or object_.get("id", "Detached container"),
                "detail": f"{location} · Capacity {float(object_.get('capacity', 0) or 0):g} ECE · Contents not exposed by API",
                "resourceType": "unknown",
                "amount": None,
            })

    @staticmethod
    def _resource_row(scope, location, resource_type, amount, detail, unit="ECE"):
        label = str(resource_type or "unknown").replace("_", " ").upper()
        value = float(amount or 0)
        return {
            "scope": scope,
            "title": f"{location} · {label}",
            "detail": f"{value:g} {unit} · {detail}",
            "resourceType": resource_type,
            "amount": value,
            "sourceType": scope,
        }

    def _galaxy_view(self, world, focus_coordinates):
        galaxy = getattr(world, "galaxy", None)
        records = galaxy.sectors() if galaxy is not None else ()
        owned_manny_locations = []
        mannies_by_sector = {}
        for manny in (world.mannies or {}).get("mannies", ()):
            location = manny.get("location") or {}
            relative = (location.get("sector") or {}).get("relative")
            if location.get("type") == "probe" or not isinstance(relative, dict):
                continue
            if not all(axis in relative for axis in ("x", "y", "z")):
                continue
            row = {
                "id": str(manny.get("id", "")),
                "name": manny.get("name", "Manny"),
                "x": int(relative["x"]),
                "y": int(relative["y"]),
                "z": int(relative["z"]),
                "locationType": str(location.get("type", "sector")),
                "currentTask": manny.get("currentTask"),
                "canReceiveOrders": bool(manny.get("canReceiveOrders", False)),
            }
            owned_manny_locations.append(row)
            key = f"{row['x']}:{row['y']}:{row['z']}"
            mannies_by_sector.setdefault(key, []).append(row)
        nodes = []
        for record in records:
            coordinate = record.coordinates
            observation = record.observed or {}
            sector = observation.get("sector", observation)
            objects = sector.get("objects", ()) or ()
            object_types = [str(item.get("type", "unknown")) for item in objects]
            resource_types = self._galaxy_resource_types(sector, objects)
            hazard_types = self._galaxy_hazard_types(sector, objects)
            max_planet_habitability = self._galaxy_max_planet_habitability(objects)
            has_detached_containers = any(
                "container" in str(item.get("type") or item.get("kind") or "").casefold()
                for item in objects
            )
            knowledge = str(sector.get("knowledgeLevel", "unknown"))
            is_focused = coordinate.x == focus_coordinates.get("x") and coordinate.y == focus_coordinates.get("y") and coordinate.z == focus_coordinates.get("z")
            if is_focused:
                map_state = "current"
            elif record.visit_count:
                map_state = "visited"
            elif record.observed:
                # Every persisted observation originates from sector scanning.
                # The API's varying knowledgeLevel values describe scan detail,
                # not a separate player-facing discovery state.
                map_state = "scanned"
            else:
                # GalaxyMap records without either a visit or observation do
                # not represent discovered sectors and are not rendered.
                continue
            node_id = f"{coordinate.x}:{coordinate.y}:{coordinate.z}"
            nodes.append({
                "id": node_id,
                "x": coordinate.x,
                "y": coordinate.y,
                "z": coordinate.z,
                "label": self._sector_label({"x": coordinate.x, "y": coordinate.y, "z": coordinate.z}),
                "visitCount": record.visit_count,
                "lastVisitedAt": record.last_visited_at or "",
                "probeIds": sorted(record.observed_by_probe_ids),
                "objectCount": len(objects),
                "objectTypes": object_types,
                "objects": tuple(self._sector_object(item) for item in objects),
                "resourceTypes": resource_types,
                "hasKnownResources": bool(resource_types),
                "hasHazard": bool(hazard_types),
                "hazardTypes": hazard_types,
                "hasDetachedContainers": has_detached_containers,
                "maxPlanetHabitability": max_planet_habitability,
                "hasHabitablePlanet": (
                    max_planet_habitability is not None
                    and max_planet_habitability >= 0.5
                ),
                "ownedMannies": tuple(mannies_by_sector.get(node_id, ())),
                "ownedMannyCount": len(mannies_by_sector.get(node_id, ())),
                "knowledgeLevel": knowledge,
                "confidence": float(sector.get("confidence", 0) or 0),
                "isFocused": is_focused,
                "mapState": map_state,
            })
        edges = []
        for index, source in enumerate(nodes):
            for target in nodes[index + 1:]:
                if max(abs(source[axis] - target[axis]) for axis in ("x", "y", "z")) == 1:
                    edges.append({"from": source["id"], "to": target["id"]})
        recent_route = self._recent_galaxy_route(world, nodes)
        recent_nodes = self._recent_galaxy_nodes(world, nodes)
        scut_ranges = []
        scut_coverage_cells = {}
        seen_relays = set()
        for response in getattr(world, "hazard_context", {}).get("scutNetworks", ()):
            network = response.get("network", {})
            for relay in network.get("relays", ()):
                relative = (relay.get("sector") or {}).get("relative")
                relay_id = str(relay.get("id") or "")
                if not relative or relay.get("status") != "on" or relay_id in seen_relays:
                    continue
                seen_relays.add(relay_id)
                relay_coordinates = SectorCoordinates.from_api(relative)
                radius = max(0, int(relay.get("coverageRadiusSectors", 0) or 0))
                scut_ranges.append({
                    "id": relay_id,
                    "x": int(relative.get("x", 0)),
                    "y": int(relative.get("y", 0)),
                    "z": int(relative.get("z", 0)),
                    "radius": radius,
                    "networkName": network.get("name", "SCUT network"),
                })
                # FCC coverage is a graph-distance volume, not an axis-aligned
                # cube. Export the exact valid lattice cells so the map and
                # travel preflight share the same boundary calculation.
                for x in range(relay_coordinates.x - radius, relay_coordinates.x + radius + 1):
                    for y in range(relay_coordinates.y - radius, relay_coordinates.y + radius + 1):
                        for z in range(relay_coordinates.z - radius, relay_coordinates.z + radius + 1):
                            if (x + y + z) % 2:
                                continue
                            coordinates = SectorCoordinates(x, y, z)
                            if relay_coordinates.distance_to(coordinates) > radius:
                                continue
                            key = f"{x}:{y}:{z}"
                            cell = scut_coverage_cells.setdefault(key, {
                                "id": key, "x": x, "y": y, "z": z,
                                "networkNames": [], "relayIds": [],
                            })
                            if network.get("name", "SCUT network") not in cell["networkNames"]:
                                cell["networkNames"].append(network.get("name", "SCUT network"))
                            cell["relayIds"].append(relay_id)
        covered_coordinates = {
            SectorCoordinates(cell["x"], cell["y"], cell["z"])
            for cell in scut_coverage_cells.values()
        }
        # Render only the exterior shell of the union. This preserves the exact
        # FCC coverage boundary while avoiding a dense cloud of interior cells,
        # and it removes internal faces where relay coverage overlaps.
        scut_coverage_boundary = tuple(
            cell for cell in scut_coverage_cells.values()
            if any(
                neighbor not in covered_coordinates
                for neighbor in SectorCoordinates(
                    cell["x"], cell["y"], cell["z"],
                ).neighbors()
            )
        )
        result = {
            "nodes": tuple(nodes),
            # Camera centering must not depend on the focused sector already
            # existing in the persisted discovery graph. A newly arrived or
            # partially refreshed probe can legitimately have no matching
            # rendered node yet.
            "focusCoordinates": ({
                "x": int(focus_coordinates["x"]),
                "y": int(focus_coordinates["y"]),
                "z": int(focus_coordinates["z"]),
            } if all(axis in focus_coordinates for axis in ("x", "y", "z")) else None),
            "focusProbeId": world.probe.get("id"),
            "edges": tuple(edges),
            "sectorCount": len(nodes),
            "unknownNeighborCount": 0,
            "recentTrail": recent_route,
            "recentTrailNodes": recent_nodes,
            "recentTrailCount": len(recent_route),
            "recentTrailProbeId": world.probe.get("id"),
            "scutRanges": tuple(scut_ranges),
            "scutCoverageCells": tuple(scut_coverage_cells.values()),
            "scutCoverageBoundary": scut_coverage_boundary,
            "ownedMannyLocations": tuple(owned_manny_locations),
        }
        # The controller refreshes global dashboard objects frequently even
        # when durable galaxy knowledge is unchanged. Compute the revision in
        # the worker-built presentation layer so QML can retain its expensive
        # 3D delegate population across equivalent refreshes.
        result["revision"] = hashlib.sha1(
            json.dumps(result, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        return result

    def _communications(self, probe):
        if not self.operations.messaging:
            return {"inbox": (), "outbox": (), "unreadCount": 0}
        inbox = tuple(self.operations.messaging.inbox(probe.get("id")))
        outbox = tuple(self.operations.messaging.outbox())
        unread = sum(
            not bool(message.get("read", message.get("isRead", message.get("status") == "read")))
            for message in inbox
        )
        return {"inbox": inbox, "outbox": outbox, "unreadCount": unread}

    @classmethod
    def _movement_view(cls, probe):
        navigation = probe.get("navigation") or {}
        movement = dict(
            probe.get("movement") or probe.get("travel")
            or navigation.get("movement") or navigation.get("travel") or {}
        )
        def first(*keys):
            for key in keys:
                value = movement.get(key)
                if value not in (None, "", {}):
                    return value
            return None
        def coordinate_label(value):
            if not isinstance(value, dict):
                return value
            value = value.get("relative") or value.get("relativeCoordinates") or value
            if all(axis in value for axis in ("x", "y", "z")):
                return f"{value['x']}:{value['y']}:{value['z']}"
            return None
        origin = first("originSector", "origin", "from", "departureSector")
        destination = first("arrivalSector", "destinationSector", "destination", "target", "to")
        estimated_arrival = first("estimatedArrival", "arrivalAt", "arrivalTime", "eta")
        remaining_time = first("remainingTime", "timeRemaining", "remainingSeconds", "secondsRemaining")
        arrival_epoch_ms = cls._travel_arrival_epoch_ms(estimated_arrival, remaining_time)
        movement.update({
            "originLabel": coordinate_label(origin) or first("originLabel") or "UNKNOWN",
            "destinationLabel": coordinate_label(destination) or first("destinationLabel") or "UNKNOWN",
            "estimatedArrival": estimated_arrival,
            "remainingTime": remaining_time,
            "arrivalEpochMs": arrival_epoch_ms,
            "velocity": first("velocity", "velocityC", "speedC") or probe.get("velocity", probe.get("velocityC", probe.get("speedC"))) or navigation.get("velocity", navigation.get("velocityC", navigation.get("speedC"))),
            "heading": first("heading", "vector", "direction", "headingVector") or probe.get("heading", probe.get("headingVector")) or navigation.get("heading", navigation.get("headingVector")),
        })
        return movement

    @staticmethod
    def _travel_arrival_epoch_ms(estimated_arrival, remaining_time):
        if estimated_arrival:
            try:
                parsed = datetime.fromisoformat(
                    str(estimated_arrival).replace("Z", "+00:00")
                )
                return int(parsed.timestamp() * 1000)
            except (TypeError, ValueError):
                pass
        try:
            seconds = float(remaining_time)
        except (TypeError, ValueError):
            return 0
        return int(datetime.now().timestamp() * 1000 + max(0, seconds) * 1000)

    @staticmethod
    def _iso_epoch_ms(value):
        if not value:
            return 0
        try:
            return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp() * 1000)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _normalized_resource_type(value):
        normalized = str(value or "").strip().casefold().replace(" ", "_").replace("-", "_")
        if normalized in {
            "organic_compound", "organic_compounds",
            "carbon_compound", "carbon_compounds",
        }:
            return "carbon_compounds"
        return normalized

    @classmethod
    def _galaxy_resource_types(cls, sector, objects):
        """Return filterable resources from durable, non-depleted sources.

        Direct asteroid objects are the game's finite wandering asteroids. They
        remain visible in sector details, but are deliberately excluded from
        galaxy-wide resource filters. Persistent solar-system targets are
        represented by nested ``minableTargets`` entries and remain eligible
        only while their authoritative remaining amount is positive.
        """
        found = set()

        def collect(value):
            if isinstance(value, dict):
                for key, amount in value.items():
                    try:
                        present = float(amount or 0) > 0
                    except (TypeError, ValueError):
                        present = bool(amount)
                    if present:
                        found.add(cls._normalized_resource_type(key))
            elif isinstance(value, (list, tuple, set)):
                for item in value:
                    if isinstance(item, dict):
                        resource_type = item.get("type") or item.get("resourceType") or item.get("name")
                        amount = item.get("amount", item.get("remaining", 1))
                        if resource_type and amount not in (0, 0.0, "0", None):
                            found.add(cls._normalized_resource_type(resource_type))
                    elif item:
                        found.add(cls._normalized_resource_type(item))

        candidates = [
            object_ for object_ in objects
            if str(object_.get("type") or object_.get("kind") or "").casefold()
            != "asteroid"
        ]
        candidates.extend(
            target
            for object_ in objects
            for target in (object_.get("minableTargets", ()) or ())
            if isinstance(target, dict) and any(
                float(amount or 0) > 0
                for amount in (target.get("resourceAmounts") or {}).values()
            )
        )
        for candidate in candidates:
            for key in (
                "resourceAmounts", "resources", "resourceTypes", "resourceComposition",
                "composition", "remainingResources",
            ):
                collect(candidate.get(key))
        return sorted(item for item in found if item)

    @staticmethod
    def _galaxy_max_planet_habitability(objects):
        """Return the best exact known planet score in a sector observation."""
        scores = []
        pending = list(objects or ())
        while pending:
            item = pending.pop()
            if not isinstance(item, dict):
                continue
            type_ = str(item.get("type") or item.get("kind") or "").casefold()
            if type_ == "planet" or type_.endswith("_planet"):
                score = item.get("habitabilityScore")
                try:
                    if score is not None:
                        scores.append(float(score))
                except (TypeError, ValueError):
                    pass
            for key in ("objects", "bookmarkTargets", "minableTargets"):
                nested = item.get(key) or ()
                if isinstance(nested, (list, tuple)):
                    pending.extend(nested)
        return max(scores) if scores else None

    @staticmethod
    def _galaxy_hazard_types(sector, objects):
        hazards = set()
        for value in sector.get("hazards", ()) or ():
            if isinstance(value, dict):
                hazards.add(str(value.get("type") or value.get("code") or "hazard"))
            else:
                hazards.add(str(value))
        dangerous_types = {"black_hole", "anomaly", "singularity", "hostile", "hazard"}
        for object_ in objects:
            type_ = str(object_.get("type") or object_.get("kind") or "unknown").casefold()
            danger = str(object_.get("dangerLevel") or object_.get("danger") or "").casefold()
            if type_ in dangerous_types or danger not in {"", "none", "safe", "low", "unknown", "0"}:
                hazards.add(type_ if type_ != "unknown" else danger)
        return sorted(hazards)

    def _recent_galaxy_route(self, world, nodes, limit=10):
        if self.data_engine is None or world.probe.get("id") is None:
            return ()
        known_ids = {node["id"] for node in nodes}
        points = []
        route_loader = getattr(self.data_engine, "probe_route", None)
        if route_loader is not None:
            history = reversed(route_loader(world.probe["id"], limit))
            for item in history:
                identifier = ":".join(str(value) for value in item["point"])
                if identifier in known_ids:
                    points.append({"id": identifier, "visitedAt": item["observed_at"] or ""})
        else:
            visits = list(self.data_engine.visits(world.probe["id"]))[:limit]
            for visit in reversed(visits):
                identifier = f"{visit['sector_x']}:{visit['sector_y']}:{visit['sector_z']}"
                if identifier in known_ids and (not points or points[-1]["id"] != identifier):
                    points.append({"id": identifier, "visitedAt": visit["last_visited_at"] or ""})
        return tuple(
            {
                "from": source["id"], "to": target["id"], "sequence": index + 1,
                "fromVisitedAt": source["visitedAt"], "toVisitedAt": target["visitedAt"],
            }
            for index, (source, target) in enumerate(zip(points, points[1:]))
        )

    def _recent_galaxy_nodes(self, world, nodes, limit=10):
        if self.data_engine is None or world.probe.get("id") is None:
            return ()
        known_ids = {node["id"] for node in nodes}
        route_loader = getattr(self.data_engine, "probe_route", None)
        if route_loader is not None:
            return tuple(
                identifier for item in route_loader(world.probe["id"], limit)
                if (identifier := ":".join(str(value) for value in item["point"])) in known_ids
            )
        return tuple(identifier for visit in self.data_engine.visits(world.probe["id"])[:limit]
                     if (identifier := f"{visit['sector_x']}:{visit['sector_y']}:{visit['sector_z']}") in known_ids)

    @staticmethod
    def _coordinates(probe, world_sector=None):
        sector = probe.get("sector") or {}
        coordinates = sector.get("relative") or sector.get("relativeCoordinates")
        if coordinates:
            return coordinates
        # Reachable-probe GET /probe records may omit sector coordinates even
        # though the authoritative GET /probe/{id}/sector response contains
        # them. Use that live snapshot before declaring the location unknown.
        snapshot = (world_sector or {}).get("snapshot") or {}
        snapshot_sector = snapshot.get("sector") or snapshot
        return (
            snapshot_sector.get("relative")
            or snapshot_sector.get("relativeCoordinates")
            or {}
        )

    @staticmethod
    def _sector_label(coordinates):
        if not coordinates:
            return "SECTOR UNKNOWN"
        return "FCC {x} / {y} / {z}".format(
            x=coordinates.get("x", "?"),
            y=coordinates.get("y", "?"),
            z=coordinates.get("z", "?"),
        )

    @staticmethod
    def _resources(probe):
        inventory = probe.get("inventory", {})
        stocks = inventory.get("resourceStocks", ())
        capacity = float(inventory.get("capacity", 0) or 0)
        fuel = probe.get("fuel", {})
        deuterium = float(fuel.get("deuterium", 0) or 0)
        maximum_deuterium = float(fuel.get("maxDeuterium", 0) or 0)
        resources = [{
            "type": "deuterium",
            "name": "Deuterium",
            "amount": deuterium,
            "capacity": maximum_deuterium,
            "label": "DEUTERIUM",
            "reading": (
                f"{(deuterium / maximum_deuterium * 100):.0f}%"
                f"  ·  {deuterium:g} / {maximum_deuterium:g}"
                if maximum_deuterium else "CAPACITY UNKNOWN"
            ),
            "value": min(1.0, deuterium / maximum_deuterium) if maximum_deuterium else 0,
        }]
        for stock in stocks:
            resource_type = stock.get("type") or stock.get("resourceType") or stock.get("name", "unknown")
            amount = float(stock.get("amount", 0) or 0)
            resources.append({
                "type": str(resource_type).lower().replace(" ", "_"),
                "name": stock.get("name") or str(resource_type).replace("_", " ").title(),
                "amount": amount,
                "capacity": capacity,
                "label": (stock.get("name") or str(resource_type).replace("_", " ")).upper(),
                "reading": MissionControlViewModelBuilder._resource_reading(amount),
                "value": min(1.0, amount / capacity) if capacity else 0,
            })
        return tuple(resources)

    @staticmethod
    def _resource_reading(amount):
        precision = 0 if amount >= 100 else 2 if amount >= 1 else 4
        return f"{amount:,.{precision}f} ECE"

    def _sector_view(self, world, coordinates):
        snapshot = (world.sector or {}).get("snapshot") or {}
        sector = snapshot.get("sector", snapshot)
        objects = []
        system = None
        sector_objects = sector.get("objects", ()) or ()
        black_holes = []
        nested_ids = set()
        for item in sector_objects:
            view = self._sector_object(item)
            if str(item.get("type", "")).casefold() == "black_hole":
                black_holes.append(item)
            if item.get("type") == "solar_system":
                system = {
                    **view,
                    "systemId": str(item.get("id") or item.get("name") or "UNKNOWN"),
                }
            else:
                is_planet = "planet" in str(item.get("type", "")).casefold()
                view["layoutRole"] = "orbital_body" if is_planet else "free_object"
                if is_planet:
                    view["orbitIndex"] = len(nested_ids)
                    nested_ids.add(str(item.get("id", f"planet-{len(nested_ids)}")))
                objects.append(view)
            nested_candidates = list(item.get("bookmarkTargets", ()) or ())
            nested_candidates.extend(item.get("minableTargets", ()) or ())
            nested_candidates.extend(item.get("objects", ()) or ())
            for child in nested_candidates:
                child_id = str(child.get("id", ""))
                if child_id and child_id in nested_ids:
                    continue
                if child_id:
                    nested_ids.add(child_id)
                orbit_index = len(nested_ids) - 1
                nested = self._sector_object(child)
                nested["parentId"] = item.get("id")
                nested["layoutRole"] = "orbital_body"
                nested["orbitIndex"] = orbit_index
                objects.append(nested)
        objects = self._condense_empty_asteroids(objects)
        active_mannies = []
        for manny in (world.mannies or {}).get("mannies", ()):
            current_task = manny.get("currentTask")
            task = manny.get("task") if isinstance(manny.get("task"), dict) else {}
            if isinstance(current_task, dict):
                task = current_task
                current_task = current_task.get("type")
            if not current_task:
                continue
            target = task.get("objectId") or task.get("targetObjectId")
            if isinstance(task.get("target"), dict):
                target = target or task["target"].get("id")
            active_mannies.append({
                "id": str(manny.get("id", manny.get("name", "manny"))),
                "name": manny.get("name", "Manny"),
                "task": str(current_task),
                "targetObjectId": str(target) if target is not None else "",
                "progress": float(manny.get("taskProgressPercent", 0) or 0),
            })
        destruction_epoch_ms = self._black_hole_destruction_epoch_ms(
            sector, snapshot, black_holes
        ) if black_holes else 0
        autonomous_units = tuple({
            "id": str(item.get("id", "")),
            "kind": str(item.get("kind", "unknown")),
            "kindLabel": str(item.get("kind", "unknown")).replace("_", " ").upper(),
            "carrierId": str((item.get("carrier") or {}).get("id", "")),
            "carrierKind": str((item.get("carrier") or {}).get("kind", "unknown")),
            "spatialState": str(item.get("spatialState", "unknown")),
            "spatialStateLabel": str(item.get("spatialState", "unknown")).replace("_", " ").upper(),
        } for item in (world.sector or {}).get("autonomousUnits", ()))
        return {
            "label": self._sector_label(coordinates),
            "knowledgeLevel": sector.get("knowledgeLevel", "unknown"),
            "confidence": float(sector.get("confidence", 0) or 0),
            "objects": tuple(objects),
            "targetedMissiles": tuple(
                item for item in objects
                if str(item.get("type", "")).casefold() == "missile"
                and item.get("targetsCurrentProbe", False)
            ),
            "system": system or {},
            "activeMannies": tuple(active_mannies),
            "autonomousUnits": autonomous_units,
            "blackHoleDanger": bool(black_holes),
            "destructionEpochMs": destruction_epoch_ms,
            "emptyReason": (
                "Detailed scan reports no celestial or artificial objects in this sector."
                if not objects and system is None and sector.get("knowledgeLevel") == "detailed"
                else ""
            ),
        }

    @staticmethod
    def _condense_empty_asteroids(objects):
        """Represent multiple depleted asteroids as one stable map marker."""
        empty = []
        visible = []
        for item in objects:
            resources = item.get("resources")
            is_asteroid = str(item.get("type", "")).casefold() == "asteroid"
            depleted = is_asteroid and (
                item.get("status") == "depleted"
                or item.get("depleted") is True
                or (isinstance(resources, dict) and bool(resources))
            )
            if depleted:
                for amount in resources.values():
                    try:
                        if float(amount or 0) > 0:
                            depleted = False
                            break
                    except (TypeError, ValueError):
                        if amount:
                            depleted = False
                            break
            (empty if depleted else visible).append(item)
        if len(empty) < 2:
            return visible + empty
        return visible + [{
            "id": "depleted-asteroids-summary",
            "type": "asteroid",
            "name": f"×{len(empty)} EMPTY ASTEROIDS",
            "category": "depleted_asteroid_group",
            "estimated": False,
            "dangerLevel": "nominal",
            "resources": {},
            "mode": "grouped",
            "status": "depleted",
            "isTransitBeacon": False,
            "layoutRole": "free_object",
            "aggregateCount": len(empty),
            "aggregateIds": tuple(item["id"] for item in empty),
        }]

    @classmethod
    def _black_hole_destruction_epoch_ms(cls, sector, snapshot, black_holes):
        """Extract a real destruction deadline without assuming one API shape."""
        deadline_keys = (
            "destructionAt", "destructionDeadline", "destroyAt", "destroyedAt",
            "hazardDeadline", "deadline", "expiresAt", "expirationTime",
        )
        remaining_keys = (
            "destructionRemainingSeconds", "secondsUntilDestruction",
            "timeToDestruction", "remainingSeconds",
        )
        sources = [sector, snapshot, *black_holes]
        for source in sources:
            if not isinstance(source, dict):
                continue
            for key in deadline_keys:
                value = source.get(key)
                epoch_ms = cls._completion_view(value)["epochMs"] if value else 0
                if epoch_ms:
                    return epoch_ms
            for key in remaining_keys:
                value = source.get(key)
                try:
                    seconds = float(value)
                except (TypeError, ValueError):
                    continue
                if seconds >= 0:
                    return int(datetime.now().timestamp() * 1000 + seconds * 1000)
        return 0

    def navigation_view(self):
        world = self.operations.world
        current = self.operations.travel.current_sector()
        if current is None:
            return {"current": {}, "neighbors": (), "travelReady": False}
        snapshot = (world.sector or {}).get("snapshot") or {}
        current_sector = snapshot.get("sector", snapshot)
        galaxy = getattr(world, "galaxy", None)
        neighbors = []
        for coordinates in current.neighbors():
            record = galaxy.get(coordinates) if galaxy is not None else None
            observed = (record.observed or {}) if record is not None else {}
            sector = observed.get("sector", observed)
            neighbors.append({
                "x": coordinates.x, "y": coordinates.y, "z": coordinates.z,
                "label": self._sector_label({"x": coordinates.x, "y": coordinates.y, "z": coordinates.z}),
                "visited": bool(record and record.visit_count),
                "visitCount": record.visit_count if record else 0,
                "knowledgeLevel": sector.get("knowledgeLevel", "unscanned"),
                "confidence": float(sector.get("confidence", 0) or 0),
                "objectCount": len(sector.get("objects", ()) or ()),
                "scanSummary": self._scan_summary(sector),
                "detailText": self._sector_detail_text(sector),
                "scutCoverage": self._scut_coverage(world, coordinates),
            })
        return {
            "current": {
                "x": current.x, "y": current.y, "z": current.z,
                "label": self._sector_label({
                    "x": current.x, "y": current.y, "z": current.z,
                }),
                "isCurrent": True,
                "visited": True,
                "knowledgeLevel": current_sector.get("knowledgeLevel", "unknown"),
                "confidence": float(current_sector.get("confidence", 0) or 0),
                "objectCount": len(current_sector.get("objects", ()) or ()),
                "scanSummary": self._scan_summary(current_sector),
                "detailText": self._sector_detail_text(current_sector),
                "scutCoverage": self._scut_coverage(world, current),
            },
            "neighbors": tuple(neighbors),
            "travelReady": self.operations.travel.travel_ready(),
            "fuelPercent": self.operations.travel.fuel_percentage(),
            "fuelAvailable": self.operations.travel.fuel_available(),
            "fuelCost": self.operations.travel.fuel_cost(),
            "probeStatus": world.probe.get("status", "unknown"),
            "telemetryAvailable": world.probe.get("telemetry_available", False),
        }

    @staticmethod
    def _scan_summary(sector):
        objects = sector.get("objects", ()) or ()
        possible = sector.get("possibleObjects", ()) or ()
        estimates = sector.get("estimatedObjects", {}) or {}
        danger = sector.get("dangerEstimate", sector.get("navigationalRisk"))
        if objects:
            system = next((item for item in objects if item.get("type") == "solar_system"), None)
            if system:
                orbitals = system.get("bookmarkTargets", ()) or system.get("objects", ()) or ()
                planets = sum("planet" in str(item.get("type", "")).lower() for item in orbitals)
                stars = sum(item.get("type") == "star" for item in orbitals) or 1
                return f"Solar system: {planets} planets among {len(orbitals)} orbital objects, around {stars} star{'s' if stars != 1 else ''}."
            types = {str(item.get("type") or "object").replace("_", " ") for item in objects}
            if "black hole" in types:
                return "Hazardous sector: black hole detected."
            if "dust cloud" in types:
                return "Possible dust cloud in the sector."
            return "Known sector objects: " + ", ".join(sorted(types)) + "."
        if possible:
            return "Possible: " + ", ".join(str(item).replace("_", " ") for item in possible)
        if estimates:
            black_hole = float(estimates.get("blackHoleProbability", 0) or 0)
            dust = float(estimates.get("dustCloudProbability", 0) or 0)
            minimum = int(estimates.get("planetCountMin", 0) or 0)
            maximum = int(estimates.get("planetCountMax", 0) or 0)
            has_star = bool(estimates.get("star", estimates.get("hasStar", False)))
            if black_hole >= 0.5:
                return "Hazardous sector: possible black hole detected."
            if dust >= 0.5:
                return "Possible dust cloud in the sector."
            if has_star or minimum > 0 or maximum > 1:
                return f"Probable stellar system: {minimum} to {maximum} planets estimated."
            return "No major nearby object estimated."
        if danger and str(danger).lower() not in {"unknown", "none", "safe"}:
            return "Hazard estimate: " + str(danger).replace("_", " ")
        knowledge = str(sector.get("knowledgeLevel", "unscanned"))
        return "Empty sector" if knowledge in {"detailed", "scanned", "full"} else "Long-range details unavailable"

    @staticmethod
    def _sector_detail_text(sector):
        """Keep precise planet telemetry available to the scanning UI."""
        objects = sector.get("objects", ()) or ()
        orbitals = []
        for system in (item for item in objects if item.get("type") == "solar_system"):
            orbitals.extend(system.get("bookmarkTargets", ()) or system.get("objects", ()) or ())
        if not orbitals:
            orbitals = list(objects)
        planets = [item for item in orbitals if "planet" in str(item.get("type", "")).lower()]
        lines = [MissionControlViewModelBuilder._scan_summary(sector)]
        if not planets:
            lines.append("No detailed planet composition is available for this sector.")
        for index, planet in enumerate(planets, 1):
            name = planet.get("name") or f"Planet {index}"
            category = str(planet.get("category") or "unknown").replace("_", " ").title()
            habitability = planet.get("habitabilityScore")
            score = "unknown" if habitability is None else f"{float(habitability):.6f}"
            physical = []
            if planet.get("mass") is not None:
                physical.append(f"mass {float(planet['mass']):g} Earth masses")
            if planet.get("radius") is not None:
                physical.append(f"radius {float(planet['radius']):g} Earth radii")
            life = "yes" if planet.get("intelligentLife") is True else "no" if planet.get("intelligentLife") is False else "unknown"
            lines.append(
                f"{name} · composition/category: {category} · habitability: {score} · "
                + (" · ".join(physical) + " · " if physical else "")
                + f"intelligent life: {life}"
            )
        return "\n\n".join(lines)

    @staticmethod
    def _scut_coverage(world, coordinates):
        for response in getattr(world, "hazard_context", {}).get("scutNetworks", ()):
            network = response.get("network", {})
            for relay in network.get("relays", ()):
                relative = (relay.get("sector") or {}).get("relative")
                if not relative or relay.get("status") != "on":
                    continue
                relay_coordinates = SectorCoordinates.from_api(relative)
                if relay_coordinates.distance_to(coordinates) <= int(relay.get("coverageRadiusSectors", 0)):
                    return {"covered": True, "networkName": network.get("name", "SCUT network"), "relayId": relay.get("id")}
        return {"covered": False, "networkName": "", "relayId": None}

    @staticmethod
    def _sector_object(item):
        object_type = re.sub(
            r"([a-z0-9])([A-Z])", r"\1_\2", str(item.get("type", "unknown"))
        ).strip().lower().replace("-", "_").replace(" ", "_")
        if MissionControlViewModelBuilder._is_others_mothership_wreck(
            item, object_type,
        ):
            object_type = "others_mothership_wreck"
        elif str(item.get("observedClass", "")).casefold() in {
            "large_ship", "ship",
        }:
            object_type = "others_ship"
        view = {
            "id": str(item.get("id", "unknown")),
            "type": object_type,
            "name": item.get("name") or item.get("summary") or item.get("type", "Unknown").replace("_", " ").title(),
            "category": item.get("category"),
            "mass": item.get("mass"),
            "massUnit": item.get("massUnit"),
            "radius": item.get("radius"),
            "radiusUnit": item.get("radiusUnit"),
            "estimated": bool(item.get("estimated", False)),
            "dangerLevel": item.get("dangerLevel", "unknown"),
            # API v122 supplies both human resource hints and authoritative
            # remaining amounts. Depletion/grouping must use the latter even
            # when the hint list is non-empty (including older persisted scans).
            "resources": (
                item.get("resourceAmounts")
                if "resourceAmounts" in item
                else item.get("resources") or {}
            ),
            "mode": item.get("mode"),
            "status": item.get("status"),
            "observedClass": item.get("observedClass"),
            "movement": item.get("movement") or {},
            "isTransitBeacon": bool(item.get("isTransitBeacon", False)),
            "resourceTypes": tuple(item.get("resourceTypes") or ()),
            "resourceComposition": item.get("resourceComposition") or {},
            "resourceAmounts": item.get("resourceAmounts") or {},
            "habitabilityScore": item.get("habitabilityScore"),
            "mannyMineable": bool(item.get("mannyMineable", False)),
            "harvestedByOthers": bool(item.get("harvestedByOthers", False)),
            "launcherKind": item.get("launcherKind"),
            "targetKind": item.get("targetKind"),
            "targetId": str(item.get("targetId", "")),
            "launchedAt": item.get("launchedAt"),
            "impactAt": item.get("impactAt"),
            "impactEpochMs": MissionControlViewModelBuilder._iso_epoch_ms(item.get("impactAt")),
            "targetsCurrentProbe": bool(item.get("targetsCurrentProbe", False)),
        }
        return view

    @staticmethod
    def _is_others_mothership_wreck(item, normalized_type=None):
        """Recognize the additive wreck representation despite its missing enum value."""
        object_type = normalized_type or str(item.get("type", "")).casefold()
        return (
            "wreck" in object_type
            or "mothership_wreck" in object_type
            or (
                item.get("massUnit") == "kilogram"
                and item.get("radiusUnit") == "meter"
                and (
                    "wreck" in str(item.get("name", "")).casefold()
                    or "wreck" in str(item.get("summary", "")).casefold()
                    or "mothership" in str(item.get("name", "")).casefold()
                    or "mothership" in str(item.get("summary", "")).casefold()
                )
            )
        )

    def _event_alerts(self):
        alerts = []
        for event in self.operations.events.timeline(self.operations.world.probe["id"]) if self.operations.events else ():
            if event["domain"] not in {"alerts", "damage_warnings"}:
                continue
            payload = event.get("payload", {})
            phase = str(payload.get("phase") or payload.get("code") or "")
            summary = payload.get("title") or payload.get("message") or payload.get("summary") or event["domain"].replace("_", " ").title()
            destruction_epoch_ms = self._iso_epoch_ms(payload.get("scheduledAt"))
            remote_manny_targeted = (
                phase == "weapon_targeted"
                and "manny" in str(summary).casefold()
                and not payload.get("resolvedAt")
                and destruction_epoch_ms > datetime.now().timestamp() * 1000
            )
            sector = payload.get("sector") or {}
            relative_sector = sector.get("relative") or sector.get("relativeCoordinates") or {}
            alerts.append({
                "id": str(event.get("id", "event")),
                "domain": event["domain"],
                "deletable": True,
                "code": str(payload.get("code") or phase or event.get("id", "event")),
                "phase": phase,
                "severity": "critical" if phase == "weapon_targeted" else payload.get("severity", event.get("priority", "warning")),
                "summary": summary,
                "illustrationImageUrl": payload.get("illustrationImageUrl"),
                "entity_id": payload.get("probeId"),
                "remoteMannyLaserTargeted": remote_manny_targeted,
                "sector": relative_sector,
                "sectorLabel": self._sector_label(relative_sector),
                "destructionEpochMs": destruction_epoch_ms,
                "observedAt": (
                    payload.get("createdAt")
                    or payload.get("updatedAt")
                    or event.get("observedAt", "")
                ),
            })
        return tuple(alerts)

    def _dashboard_alerts(self, findings):
        received = sorted(
            self._event_alerts(),
            key=lambda item: item.get("observedAt", ""),
            reverse=True,
        )
        source = received if received else findings
        # Mission Control limits its own preview to three cards. Safety needs
        # the complete game collection for the focused probe, including
        # acknowledged historical alerts that remain deletable.
        return self._alert_views(tuple(source))

    @staticmethod
    def _alert_views(alerts):
        return tuple({
            **item,
            "codeLabel": str(item.get("code", "alert")).replace("_", " ").upper(),
        } for item in alerts)

    def _missions(self):
        if not self.operations.missions:
            return ()
        missions = []
        for item in self.operations.missions.all():
            name = item.get("name") or item.get("title") or "Mission"
            status = item.get("status", "unknown")
            if status not in {"active", "accepted", "in_progress"}:
                continue
            progress = float(self.operations.missions.progress(item) or 0)
            description = item.get("description") or item.get("objective") or item.get("summary") or "No additional mission description is available."
            missions.append({
                "id": str(item.get("id", item.get("uid", "mission"))),
                "name": name,
                "status": status,
                "progress": progress,
                "displayText": f"◇  {name}    {str(status).upper()}    {progress:.0f}%",
                "detailText": f"Status: {str(status).replace('_', ' ').title()}\nProgress: {progress:.1f}%\n{description}",
            })
        return tuple(missions)

    @staticmethod
    def _production(probe, mannies, automation_reasons=None):
        automation_reasons = automation_reasons or {}
        work = []
        printer_assistance_tasks = []
        inventory = probe.get("inventory", {}) or {}
        storage_free = float(inventory.get("freeCapacity", 0) or 0)
        for manny in (mannies or {}).get("mannies", ()):
            task_type = manny.get("currentTask")
            if not task_type:
                ready = bool(manny.get("canReceiveOrders", False))
                location = manny.get("location") or {}
                relative = (location.get("sector") or {}).get("relative") or {}
                location_text = (
                    f"FCC {relative['x']} / {relative['y']} / {relative['z']}"
                    if all(axis in relative for axis in ("x", "y", "z"))
                    else "Aboard probe" if location.get("type") == "probe"
                    else "Coordinates unavailable"
                )
                work.append({
                    "id": str(manny.get("id", manny.get("name", len(work)))),
                    "asset": manny.get("name", "Manny"),
                    "taskType": "idle",
                    "name": "Idle · Ready" if ready else "Idle · Unavailable",
                    "progress": 0,
                    "eta": "—",
                    "displayText": f"{manny.get('name', 'MANNY')} · IDLE · {'READY' if ready else 'UNAVAILABLE'}",
                    "detailText": (
                        f"Asset: {manny.get('name', 'Manny')}\n"
                        f"Status: Idle\nLocation: {location_text}\n"
                        f"Can receive automation order: {'Yes' if ready else 'No'}"
                    ),
                })
                continue
            task = manny.get("task") if isinstance(manny.get("task"), dict) else {}
            if str(task_type).lower().replace("-", "_") == "assisting_atomic_printer":
                printer_assistance_tasks.append(task)
            progress = float(manny.get("taskProgressPercent", 0) or 0)
            eta = manny.get("taskEstimatedEndTime") or "—"
            eta_view = MissionControlViewModelBuilder._completion_view(eta)
            started_view = MissionControlViewModelBuilder._completion_view(
                manny.get("taskStartTime")
            )
            operation = MissionControlViewModelBuilder._task_name(task_type, task)
            normalized_task = str(task_type).lower().replace("-", "_")
            target_amount = float(task.get("targetAmount", 0) or 0)
            deposited_amount = float(task.get("depositedAmount", 0) or 0)
            return_capacity_required = (
                max(0.0, target_amount - deposited_amount) + 0.05
                if normalized_task == "mining" else 0.0
            )
            storage_block_risk = (
                return_capacity_required > 0
                and storage_free + 0.000001 < return_capacity_required
            )
            automation_reason = automation_reasons.get(str(manny.get("id")))
            reason_line = (
                f"Automation reason: {automation_reason}"
                if automation_reason
                else "Task origin: No matching Skunkworks automation order is recorded; this task may have been assigned manually or by the game."
            )
            work.append({
                "id": str(manny.get("id", manny.get("name", len(work)))),
                "asset": manny.get("name", "Manny"),
                "taskType": task_type,
                "name": operation,
                "progress": progress,
                "eta": eta_view["label"],
                "etaEpochMs": eta_view["epochMs"],
                "startedAt": started_view["label"],
                "startedAtEpochMs": started_view["epochMs"],
                "storageFree": storage_free,
                "returnCapacityRequired": return_capacity_required,
                "storageBlockRisk": storage_block_risk,
                "automationReason": automation_reason or "",
                "displayText": f"{manny.get('name', 'MANNY')} · {operation.upper()}    {progress:.0f}%",
                "detailText": MissionControlViewModelBuilder._task_details(
                    manny.get("name", "Manny"), task_type, task, progress,
                    eta_view["label"],
                ) + (
                    f"\nStarted: {started_view['label']}"
                    if started_view["epochMs"] else ""
                ) + (
                    "\nStorage warning: Insufficient probe storage for this Manny "
                    f"and its remaining cargo ({return_capacity_required:.3f} ECE required; "
                    f"{storage_free:.3f} ECE free)."
                    if storage_block_risk else ""
                ) + "\n" + reason_line,
            })

        for item in probe.get("inventory", {}).get("items", ()):
            if item.get("type") != "atomic_3d_printer" or not item.get("currentTask"):
                continue
            current = item.get("currentTask")
            task = item.get("task") if isinstance(item.get("task"), dict) else {}
            if isinstance(current, dict):
                task = {**task, **current}
                task_type = current.get("type", "crafting")
            else:
                task_type = current
            # The printer endpoint can report only "atomic_printing" while
            # the assisting Manny carries the authoritative recipe payload.
            # Merge that payload so both cards identify the same output.
            if not MissionControlViewModelBuilder._task_recipe_label(task):
                assisted = next((
                    candidate for candidate in printer_assistance_tasks
                    if MissionControlViewModelBuilder._task_recipe_label(candidate)
                ), None)
                if assisted:
                    task = {**assisted, **task}
            progress = float(item.get("taskProgressPercent", 0) or 0)
            eta = item.get("taskEstimatedEndTime") or "—"
            eta_view = MissionControlViewModelBuilder._completion_view(eta)
            operation = MissionControlViewModelBuilder._task_name(task_type, task)
            work.append({
                "id": str(item.get("id", "atomic-printer")),
                "asset": item.get("name", "Atomic printer"),
                "taskType": task_type,
                "name": operation,
                "progress": progress,
                "eta": eta_view["label"],
                "etaEpochMs": eta_view["epochMs"],
                "displayText": f"ATOMIC PRINTER · {operation.upper()}    {progress:.0f}%",
                "detailText": MissionControlViewModelBuilder._task_details(
                    item.get("name", "Atomic printer"), task_type, task,
                    progress, eta_view["label"],
                ),
            })
        return tuple(work)

    def _automation_task_reasons(self, mannies, probe_id=None):
        """Match live Manny work to the successful command that started it."""
        if not self.data_engine:
            return {}
        live = {
            str(item.get("id")): item
            for item in (mannies or {}).get("mannies", ())
            if item.get("currentTask")
        }
        if not live:
            return {}
        reasons = {}
        for row in self.data_engine.recent_successful_actions(probe_id):
            try:
                command = json.loads(row["command_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            manny_id = str(command.get("targetId"))
            if manny_id in reasons or manny_id not in live:
                continue
            if self._command_matches_live_task(command, live[manny_id]):
                reason = self._concise_automation_reason(command)
                if reason:
                    reasons[manny_id] = reason
        return reasons

    @staticmethod
    def _concise_automation_reason(command):
        """Turn an internal planner explanation into one operator-facing purpose."""
        payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        raw_reason = str(command.get("reason") or "").strip()
        command_type = command.get("type")

        if command_type == "manny_mine":
            resources = payload.get("resources") or ("resource",)
            resource = str(resources[0]).replace("carbon_compounds", "organic_compound")
            resource = resource.replace("_", " ").title()
            metadata = command.get("metadata") if isinstance(command.get("metadata"), dict) else {}
            amount = float(metadata.get("orderAmount", payload.get("targetAmount", 0)) or 0)
            action = f"Mine {amount:g} ECE {resource}"
        elif command_type == "manny_craft":
            recipe = str(payload.get("recipe") or "item").replace("_", " ").title()
            action = f"Craft one {recipe}"
        else:
            return raw_reason

        if command_type == "manny_craft" and (
            "tanker component" in raw_reason.lower()
            or "tanker goal" in raw_reason.lower()
        ):
            return f"{action}. Required for Tanker Assembly. Dispatched by Skunkworks."

        purpose_text = raw_reason
        marker = "This mining order unlocks "
        if marker in purpose_text:
            purpose_text = purpose_text.split(marker, 1)[1]
        clauses = [item.strip().rstrip(".") for item in purpose_text.split(";") if item.strip()]
        preferred = next(
            (
                clause for label in (
                    "tanker component:",
                    "next production unit:",
                    "remaining production target:",
                    "production target:",
                    "reserve target",
                )
                for clause in clauses
                if label in clause.lower()
            ),
            "",
        )
        if preferred:
            preferred = preferred.replace("production target:", "production target:")
            return f"{action}. Supports {preferred}."
        return f"{action}. Dispatched by Skunkworks automation."

    @staticmethod
    def _command_matches_live_task(command, manny):
        task_type = manny.get("currentTask")
        task = manny.get("task") if isinstance(manny.get("task"), dict) else {}
        payload = command.get("payload") if isinstance(command.get("payload"), dict) else {}
        command_type = command.get("type")
        if task_type == "crafting" and command_type == "manny_craft":
            live_recipe = task.get("recipe") or task.get("recipeId")
            return not live_recipe or payload.get("recipe") == live_recipe
        if task_type == "mining" and command_type == "manny_mine":
            live_target = task.get("objectId") or task.get("targetId")
            if live_target and str(payload.get("objectId")) != str(live_target):
                return False
            live_resources = set(task.get("resourceTypes") or [task.get("resourceType")])
            ordered_resources = set(payload.get("resources") or ())
            live_resources.discard(None)
            return not live_resources or bool(live_resources & ordered_resources)
        return False

    @staticmethod
    def _completion_view(value):
        """Present an API timestamp in the operator's local timezone."""
        if not value or value == "—":
            return {"label": "—", "epochMs": 0}
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.astimezone()
            local = parsed.astimezone()
        except (TypeError, ValueError, OverflowError):
            return {"label": str(value), "epochMs": 0}

        offset = local.strftime("%z")
        offset = f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else offset
        zone = local.tzname() or "LOCAL"
        return {
            "label": f"{local:%Y-%m-%d}  {local:%H:%M:%S} {zone} (UTC{offset})",
            "epochMs": int(parsed.timestamp() * 1000),
        }

    @staticmethod
    def _task_name(task_type, task):
        recipe = MissionControlViewModelBuilder._task_recipe_label(task)
        if task_type == "crafting" or recipe:
            return f"Crafting {recipe}" if recipe else "Crafting"
        if task_type == "mining":
            resources = task.get("resourceTypes") or [task.get("resourceType")]
            resources = [str(item).replace("_", " ").title() for item in resources if item]
            return "Mining " + (", ".join(resources) if resources else "resources")
        if task_type == "assisting_atomic_printer":
            return "Assisting atomic printer"
        return str(task_type).replace("_", " ").title()

    @staticmethod
    def _task_recipe_label(task):
        reference = (
            task.get("recipeName")
            or task.get("recipe")
            or task.get("recipeId")
            or task.get("output")
        )
        if isinstance(reference, dict):
            reference = (
                reference.get("name")
                or reference.get("type")
                or reference.get("id")
            )
        return str(reference).replace("_", " ").title() if reference else ""

    @staticmethod
    def _task_details(asset, task_type, task, progress, eta):
        lines = [
            f"Asset: {asset}",
            f"Operation: {str(task_type).replace('_', ' ').title()}",
            f"Progress: {progress:.1f}%",
            f"Estimated completion: {eta}",
        ]
        recipe = MissionControlViewModelBuilder._task_recipe_label(task)
        if task_type == "crafting" or recipe:
            lines.append(f"Recipe: {recipe or 'Unknown'}")
            output = task.get("output")
            if isinstance(output, dict):
                lines.append(f"Output: {output.get('name') or output.get('type') or 'Unknown'}")
        elif task_type == "mining":
            target = task.get("target") if isinstance(task.get("target"), dict) else {}
            lines.append(f"Phase: {str(task.get('phase', 'unknown')).replace('_', ' ').title()}")
            target_label = (
                target.get("name")
                or task.get("targetName")
                or task.get("objectName")
                or task.get("objectId")
                or target.get("id")
                or "Unknown"
            )
            lines.append(f"Target: {target_label}")
            trip = task.get("tripIndex") or task.get("currentTrip")
            lines.append(f"Trip: {trip}" if trip is not None else "Trip: Single scheduled delivery (API v106)")
            if task.get("targetAmount") is not None:
                amount = float(task["targetAmount"] or 0)
                if task_type == "mining" and (
                    task.get("resourceType") == "deuterium"
                    or "deuterium" in (
                        task.get("resourceTypes") or task.get("resources") or ()
                    )
                ):
                    amount *= 100
                lines.append(f"Target amount: {amount:g} ECE")
            if task.get("depositedAmount") is not None:
                lines.append(f"Deposited: {task['depositedAmount']} ECE (commits at completion)")
            if progress < 100 and float(task.get("depositedAmount", 0) or 0) == 0:
                lines.append("Delivery: commits atomically at the final task deadline")
        recall_reason = str(task.get("reason") or task.get("returnReason") or "")
        if recall_reason == "target_container_departed_with_asteroid":
            lines.append("Recall reason: Target container departed with motorized asteroid")
        return "\n".join(lines)

    @staticmethod
    def _connection_state(probe, snapshot):
        if not probe.get("telemetry_available", False):
            return "limited_telemetry"
        if not snapshot:
            return "disconnected"
        if not snapshot.get("fresh", False):
            return "stale"
        return "connected"

    def _operation_records(self):
        if not self.data_engine:
            return ()
        return tuple(dict(row) for row in self.data_engine.operation_records())

    def _action_records(self):
        if not self.data_engine:
            return ()
        return tuple(dict(row) for row in self.data_engine.action_history())

    def _archive_records(self):
        if not self.data_engine:
            return ()
        return tuple(dict(row) for row in self.data_engine.archive_reports())

    def _reports(self, report_records=None, action_records=None, operation_records=None):
        if not self.data_engine:
            return {"daily": (), "archive": (), "industrial": {}}
        reports = [dict(row) for row in (report_records if report_records is not None else self.data_engine.archive_reports())]
        actions = [dict(row) for row in (action_records if action_records is not None else self.data_engine.action_history())]
        operations = [dict(row) for row in (operation_records if operation_records is not None else self.data_engine.operation_records())]
        probe_names = {
            str(item.get("id")): item.get("name") or f"Probe {item.get('id')}"
            for item in (getattr(self.operations.world, "fleet", {}) or {}).get("probes", ())
        }
        focused_probe = getattr(self.operations.world, "probe", {}) or {}
        if focused_probe.get("id") is not None:
            probe_names.setdefault(
                str(focused_probe["id"]),
                focused_probe.get("name") or f"Probe {focused_probe['id']}",
            )
        manny_names = {
            str(item.get("id")): item.get("name") or "Manny"
            for item in (getattr(self.operations.world, "mannies", {}) or {}).get("mannies", ())
            if item.get("id") is not None
        }
        categories = Counter()
        by_probe = defaultdict(Counter)
        archive = []
        for row in reversed(actions):
            command_type = str(row.get("command_type") or "unknown")
            category = (
                "Mining" if command_type == "manny_mine" else
                "Production" if command_type in {"manny_craft", "atomic_printer_craft", "manny_assemble_probe"} else
                "Travel" if command_type == "move_probe" else
                "Maintenance" if command_type == "manny_repair" else "Operations"
            )
            status = str(row.get("status") or "unknown")
            probe_id = str(row.get("probe_id"))
            categories[(category, status)] += 1
            by_probe[probe_id][category] += 1
            archive.append({
                "kind": "COMMAND", "domain": category, "status": status.upper(),
                "probeId": probe_id, "probeName": probe_names.get(probe_id, f"Probe {probe_id}"),
                "title": self._command_archive_title(row, command_type),
                "detail": self._command_archive_detail(
                    row, probe_names=probe_names, manny_names=manny_names,
                ),
                "amount": self._command_archive_amount(row),
                "timestamp": row.get("observed_at", ""),
            })
        for row in reversed(operations):
            archive.append({
                "kind": "OPERATION", "domain": "Operations", "status": str(row.get("state", "")).upper(),
                "probeId": str(row.get("probe_id") or ""),
                "probeName": probe_names.get(str(row.get("probe_id")), "Fleet"),
                "title": row.get("name") or row.get("objective") or "Operation",
                "detail": row.get("objective") or "", "timestamp": row.get("updated_at", ""),
            })
        for row in reports:
            archive.append({
                "kind": "REPORT", "domain": "Reports", "status": "RECORDED",
                "reportId": row.get("id", ""),
                "favorited": bool(row.get("favorited", False)),
                "probeId": "", "probeName": "Fleet", "title": row.get("title", "Report"),
                "detail": row.get("content", ""), "timestamp": row.get("created_at", ""),
            })
        archive.sort(key=lambda item: str(item.get("timestamp", "")), reverse=True)
        measured = tuple({
            "category": category, "status": status.upper(), "count": count,
        } for (category, status), count in sorted(categories.items()))
        utilization = tuple({
            "probeId": probe_id, "probeName": probe_names.get(probe_id, f"Probe {probe_id}"),
            "orders": sum(counts.values()),
            "breakdown": " · ".join(f"{name.upper()} {count}" for name, count in sorted(counts.items())),
        } for probe_id, counts in sorted(by_probe.items()))
        return {
            "daily": tuple({
                **row,
                "favorited": bool(row.get("favorited", False)),
                "deletesAt": DataEngine.daily_report_deletion_at(
                    row.get("id", ""), row.get("created_at", ""),
                ).isoformat(),
            } for row in reports if row.get("kind") == "daily_probe_report"),
            "archive": tuple(archive[:2000]),
            "industrial": {"measuredTotals": measured, "probeActivity": utilization},
        }

    @staticmethod
    def _command_payload(row):
        try:
            return json.loads(row.get("command_json") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}

    @classmethod
    def _command_archive_title(cls, row, command_type):
        command = cls._command_payload(row)
        payload = command.get("payload") or {}
        metadata = command.get("metadata") or {}
        if command_type == "manny_mine":
            resource = next(iter(payload.get("resources") or ()), "resource")
            return f"Mine {str(resource).replace('_', ' ').title()}"
        if command_type in {"manny_craft", "atomic_printer_craft"}:
            return f"Craft {str(payload.get('recipe') or 'item').replace('_', ' ').title()}"
        if command_type == "manny_assemble_probe":
            return f"Assemble {str(payload.get('model') or metadata.get('model') or 'probe').replace('_', ' ').title()}"
        return command_type.replace("_", " ").title()

    @classmethod
    def _command_archive_amount(cls, row):
        """Expose a sortable quantity only when the retained command recorded one."""

        command = cls._command_payload(row)
        payload = command.get("payload") or {}
        metadata = command.get("metadata") or {}
        value = (
            metadata.get("orderAmount")
            if metadata.get("orderAmount") is not None
            else payload.get("targetAmount")
            if payload.get("targetAmount") is not None
            else payload.get("amount")
        )
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _command_archive_detail(
        cls, row, *, probe_names=None, manny_names=None,
    ):
        probe_names = probe_names or {}
        manny_names = manny_names or {}
        command = cls._command_payload(row)
        payload = command.get("payload") or {}
        metadata = command.get("metadata") or {}
        parts = []
        command_type = str(row.get("command_type") or command.get("type") or "")
        target_id = command.get("targetId")
        if command_type == "manny_mine":
            resource = next(iter(payload.get("resources") or ()), metadata.get("resource"))
            amount = metadata.get("orderAmount", payload.get("targetAmount"))
            if resource:
                parts.append(f"Resource: {str(resource).replace('_', ' ').title()}")
            if amount is not None:
                parts.append(f"Ordered: {amount} ECE")
            if payload.get("objectId") is not None:
                parts.append(f"Source object: {payload['objectId']}")
            sector = metadata.get("sector") or {}
            if all(sector.get(axis) is not None for axis in ("x", "y", "z")):
                parts.append(f"Sector: {sector['x']}:{sector['y']}:{sector['z']}")
            else:
                parts.append("Sector: not recorded for this historical order")
            if metadata.get("estimatedTrips") is not None:
                parts.append(f"Estimated trips: {metadata['estimatedTrips']}")
        elif payload.get("recipe"):
            parts.append(f"Recipe: {str(payload['recipe']).replace('_', ' ').title()}")
        elif payload.get("model") or metadata.get("model"):
            parts.append(
                "Model: " + str(payload.get("model") or metadata.get("model")).replace("_", " ").title()
            )
        target = payload.get("target") or metadata.get("finalDestination")
        if isinstance(target, dict) and all(target.get(axis) is not None for axis in ("x", "y", "z")):
            parts.append(f"Destination: {target['x']}:{target['y']}:{target['z']}")
        if payload.get("targetProbeId") is not None:
            target_probe_id = str(payload["targetProbeId"])
            parts.append(
                "Target probe: " + probe_names.get(
                    target_probe_id, "name unavailable for this historical order",
                )
            )
        if payload.get("amount") is not None:
            parts.append(f"Amount: {payload['amount']} ECE")
        if payload.get("integrityPercent") is not None:
            parts.append(f"Repair target: {payload['integrityPercent']}% integrity")
        if target_id is not None and command_type.startswith("manny_"):
            parts.append(
                "Manny: " + str(
                    metadata.get("mannyName")
                    or manny_names.get(str(target_id))
                    or "name unavailable for this historical order"
                )
            )
        if command.get("reason"):
            reason = str(command["reason"])
            for probe_id, probe_name in probe_names.items():
                reason = re.sub(
                    rf"\bprobe\s+{re.escape(probe_id)}\b",
                    f"probe {probe_name}", reason, flags=re.IGNORECASE,
                )
            reason = re.sub(
                r"\bprobe\s+\d+\b", "probe with name unavailable", reason,
                flags=re.IGNORECASE,
            )
            parts.append(f"Reason: {reason}")
        try:
            blockers = json.loads(row.get("blockers_json") or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            blockers = []
        if blockers:
            parts.append("Blockers: " + " · ".join(str(value) for value in blockers))
        return "\n".join(parts) or "No additional command details were recorded."
