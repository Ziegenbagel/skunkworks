"""Stable UI view model assembled only from application services."""

from dataclasses import asdict
from datetime import datetime
import json
from src.models.galaxy import SectorCoordinates


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
        coordinates = self._coordinates(probe)
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
                "status": probe["status"],
                "isReachable": probe.get("telemetry_available", True),
                "sector": coordinates,
                "sectorLabel": self._sector_label(coordinates),
                "movement": dict(probe.get("movement") or {}),
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
                "inventoryFree": self.operations.inventory.free_capacity(),
                "mannyTotal": self.operations.mannies.total(),
                "mannyAvailable": len(self.operations.mannies.available()),
            },
            "depots": tuple(asdict(depot) for depot in self.operations.depots.all()),
            "health": health_view,
            "alerts": self._alert_views(findings + self._event_alerts()),
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
        }
        result["navigation"] = self.navigation_view()
        return result

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
        seen_targets = set()
        seen_recoverable = set()
        snapshot = (world.sector.get("snapshot") or {}).get("sector", {})
        def collect_targets(values):
            for value in values or ():
                target_type = str(value.get("type", "")).lower()
                target_kind = "planet" if "planet" in target_type else "asteroid" if "asteroid" in target_type else ""
                target_id = str(value.get("id", ""))
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
                collect_targets(value.get("objects"))
                collect_targets(value.get("minableTargets"))
                collect_targets(value.get("bookmarkTargets"))
        collect_targets(snapshot.get("objects"))
        collect_targets(snapshot.get("minableTargets"))
        detached = tuple(item for item in recoverable_objects if "container" in item["type"])
        return {
            "probeId": world.probe.get("id"),
            "probeName": world.probe.get("name", "Probe"),
            "containers": containers,
            "items": tuple(items),
            "resourcePlacements": tuple(resource_lines),
            "idleMannies": idle_mannies,
            "mannies": all_mannies,
            "sameSectorProbes": tuple(same_sector_probes),
            "sectorTargets": tuple(sector_targets),
            "miningTargets": tuple(mining_targets),
            "detachedContainers": tuple(detached),
            "recoverableObjects": tuple(recoverable_objects),
            "deuterium": float((world.probe.get("fuel") or {}).get("deuterium", world.probe.get("deuterium", 0)) or 0),
            "maxDeuterium": float((world.probe.get("fuel") or {}).get("maxDeuterium", 100) or 100),
        }

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
                "title": target.get("name") or target.get("id", "Mineable object"),
                "detail": "\n".join(reserve_lines) if reserve_lines else "No remaining mineable resources",
                "sourceType": target.get("type", "mineable_object"),
                "classification": target.get("classification", "observed"),
                "resources": amounts,
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
        nodes = []
        for record in records:
            coordinate = record.coordinates
            observation = record.observed or {}
            sector = observation.get("sector", observation)
            objects = sector.get("objects", ()) or ()
            object_types = [str(item.get("type", "unknown")) for item in objects]
            resource_types = self._galaxy_resource_types(sector, objects)
            hazard_types = self._galaxy_hazard_types(sector, objects)
            has_detached_containers = any(
                "container" in str(item.get("type") or item.get("kind") or "").casefold()
                for item in objects
            )
            knowledge = str(sector.get("knowledgeLevel", "unknown"))
            is_focused = coordinate.x == focus_coordinates.get("x") and coordinate.y == focus_coordinates.get("y") and coordinate.z == focus_coordinates.get("z")
            if is_focused:
                map_state = "current"
            elif knowledge in {"detailed", "scanned", "full"}:
                map_state = "scanned"
            elif record.visit_count:
                map_state = "visited"
            elif record.observed:
                map_state = "observed"
            else:
                map_state = "unknown"
            nodes.append({
                "id": f"{coordinate.x}:{coordinate.y}:{coordinate.z}",
                "x": coordinate.x,
                "y": coordinate.y,
                "z": coordinate.z,
                "label": self._sector_label({"x": coordinate.x, "y": coordinate.y, "z": coordinate.z}),
                "visitCount": record.visit_count,
                "lastVisitedAt": record.last_visited_at or "",
                "probeIds": sorted(record.observed_by_probe_ids),
                "objectCount": len(objects),
                "objectTypes": object_types,
                "resourceTypes": resource_types,
                "hasKnownResources": bool(resource_types),
                "hasHazard": bool(hazard_types),
                "hazardTypes": hazard_types,
                "hasDetachedContainers": has_detached_containers,
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
        return {
            "nodes": tuple(nodes),
            "edges": tuple(edges),
            "sectorCount": len(nodes),
            "recentTrail": recent_route,
            "recentTrailCount": len(recent_route),
            "recentTrailProbeId": world.probe.get("id"),
        }

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
        """Return confirmed resource types without treating unknown sectors as empty."""
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

        candidates = [sector, *objects]
        candidates.extend(
            target
            for object_ in objects
            for target in (object_.get("minableTargets", ()) or ())
            if isinstance(target, dict)
        )
        for candidate in candidates:
            for key in (
                "resourceAmounts", "resources", "resourceTypes", "resourceComposition",
                "composition", "remainingResources",
            ):
                collect(candidate.get(key))
        return sorted(item for item in found if item)

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
        visits = list(self.data_engine.visits(world.probe["id"]))[:limit]
        known_ids = {node["id"] for node in nodes}
        points = []
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

    @staticmethod
    def _coordinates(probe):
        sector = probe.get("sector") or {}
        return sector.get("relative") or sector.get("relativeCoordinates") or {}

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
        for item in sector.get("objects", ()) or ():
            view = self._sector_object(item)
            if item.get("type") == "solar_system":
                system = {
                    **view,
                    "systemId": str(item.get("id") or item.get("name") or "UNKNOWN"),
                }
            else:
                view["layoutRole"] = "free_object"
                objects.append(view)
            for orbit_index, child in enumerate(item.get("bookmarkTargets", ()) or ()):
                nested = self._sector_object(child)
                nested["parentId"] = item.get("id")
                nested["layoutRole"] = "orbital_body"
                nested["orbitIndex"] = orbit_index
                objects.append(nested)
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
        return {
            "label": self._sector_label(coordinates),
            "knowledgeLevel": sector.get("knowledgeLevel", "unknown"),
            "confidence": float(sector.get("confidence", 0) or 0),
            "objects": tuple(objects),
            "system": system or {},
            "activeMannies": tuple(active_mannies),
            "emptyReason": (
                "Detailed scan reports no celestial or artificial objects in this sector."
                if not objects and system is None and sector.get("knowledgeLevel") == "detailed"
                else ""
            ),
        }

    def navigation_view(self):
        world = self.operations.world
        current = self.operations.travel.current_sector()
        if current is None:
            return {"current": {}, "neighbors": (), "travelReady": False}
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
                "scutCoverage": self._scut_coverage(world, coordinates),
            })
        return {
            "current": {"x": current.x, "y": current.y, "z": current.z, "label": self._sector_label({"x": current.x, "y": current.y, "z": current.z})},
            "neighbors": tuple(neighbors),
            "travelReady": self.operations.travel.travel_ready(),
            "fuelPercent": self.operations.travel.fuel_percentage(),
            "fuelAvailable": self.operations.travel.fuel_available(),
            "fuelCost": self.operations.travel.fuel_cost(),
            "probeStatus": world.probe.get("status", "unknown"),
            "telemetryAvailable": world.probe.get("telemetry_available", False),
        }

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
        return {
            "id": str(item.get("id", "unknown")),
            "type": item.get("type", "unknown"),
            "name": item.get("name") or item.get("summary") or item.get("type", "Unknown").replace("_", " ").title(),
            "category": item.get("category"),
            "estimated": bool(item.get("estimated", False)),
            "dangerLevel": item.get("dangerLevel", "unknown"),
            "resources": item.get("resources") or item.get("resourceAmounts") or {},
            "mode": item.get("mode"),
            "status": item.get("status"),
            "isTransitBeacon": bool(item.get("isTransitBeacon", False)),
        }

    def _event_alerts(self):
        alerts = []
        for event in self.operations.events.timeline(self.operations.world.probe["id"]) if self.operations.events else ():
            if event["domain"] not in {"alerts", "damage_warnings"}:
                continue
            payload = event.get("payload", {})
            alerts.append({
                "code": str(event.get("id", "event")),
                "severity": payload.get("severity", event.get("priority", "warning")),
                "summary": payload.get("title") or payload.get("message") or payload.get("summary") or event["domain"].replace("_", " ").title(),
                "entity_id": payload.get("probeId"),
            })
        return tuple(alerts)

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
        for manny in (mannies or {}).get("mannies", ()):
            task_type = manny.get("currentTask")
            if not task_type:
                ready = bool(manny.get("canReceiveOrders", False))
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
                        f"Status: Idle\nCan receive automation order: {'Yes' if ready else 'No'}"
                    ),
                })
                continue
            task = manny.get("task") if isinstance(manny.get("task"), dict) else {}
            progress = float(manny.get("taskProgressPercent", 0) or 0)
            eta = manny.get("taskEstimatedEndTime") or "—"
            eta_view = MissionControlViewModelBuilder._completion_view(eta)
            operation = MissionControlViewModelBuilder._task_name(task_type, task)
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
                "automationReason": automation_reason or "",
                "displayText": f"{manny.get('name', 'MANNY')} · {operation.upper()}    {progress:.0f}%",
                "detailText": MissionControlViewModelBuilder._task_details(
                    manny.get("name", "Manny"), task_type, task, progress,
                    eta_view["label"],
                ) + "\n" + reason_line,
            })

        for item in probe.get("inventory", {}).get("items", ()):
            if item.get("type") != "atomic_3d_printer" or not item.get("currentTask"):
                continue
            task = item.get("task") if isinstance(item.get("task"), dict) else {}
            progress = float(item.get("taskProgressPercent", 0) or 0)
            eta = item.get("taskEstimatedEndTime") or "—"
            eta_view = MissionControlViewModelBuilder._completion_view(eta)
            operation = MissionControlViewModelBuilder._task_name(item["currentTask"], task)
            work.append({
                "id": str(item.get("id", "atomic-printer")),
                "asset": item.get("name", "Atomic printer"),
                "taskType": item["currentTask"],
                "name": operation,
                "progress": progress,
                "eta": eta_view["label"],
                "etaEpochMs": eta_view["epochMs"],
                "displayText": f"ATOMIC PRINTER · {operation.upper()}    {progress:.0f}%",
                "detailText": MissionControlViewModelBuilder._task_details(
                    item.get("name", "Atomic printer"), item["currentTask"], task,
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
        for row in reversed(self.data_engine.action_history(probe_id)):
            if row["status"] != "succeeded":
                continue
            try:
                command = json.loads(row["command_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            manny_id = str(command.get("targetId"))
            if manny_id in reasons or manny_id not in live:
                continue
            if self._command_matches_live_task(command, live[manny_id]):
                reason = str(command.get("reason") or "").strip()
                if reason:
                    reasons[manny_id] = reason
        return reasons

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
        if task_type == "crafting":
            return task.get("recipeName") or task.get("recipe") or "Crafting"
        if task_type == "mining":
            resources = task.get("resourceTypes") or [task.get("resourceType")]
            resources = [str(item).replace("_", " ").title() for item in resources if item]
            return "Mining " + (", ".join(resources) if resources else "resources")
        if task_type == "assisting_atomic_printer":
            return "Assisting atomic printer"
        return str(task_type).replace("_", " ").title()

    @staticmethod
    def _task_details(asset, task_type, task, progress, eta):
        lines = [
            f"Asset: {asset}",
            f"Operation: {str(task_type).replace('_', ' ').title()}",
            f"Progress: {progress:.1f}%",
            f"Estimated completion: {eta}",
        ]
        if task_type == "crafting":
            lines.append(f"Recipe: {task.get('recipeName') or task.get('recipe') or 'Unknown'}")
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
            lines.append(f"Trip: {task.get('tripIndex', '—')}")
            if task.get("targetAmount") is not None:
                lines.append(f"Target amount: {task['targetAmount']} ECE")
            if task.get("depositedAmount") is not None:
                lines.append(f"Deposited: {task['depositedAmount']} ECE")
            if progress < 100 and float(task.get("depositedAmount", 0) or 0) == 0:
                lines.append("Delivery: commits atomically at the final task deadline")
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
