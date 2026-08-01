"""Stable UI view model assembled only from application services."""

from dataclasses import asdict
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
            "sector": self._sector_view(world, coordinates),
            "galaxy": self._galaxy_view(world, coordinates),
            "missions": self._missions(),
            "production": self._production(probe, world.mannies),
            "events": self.operations.events.timeline(probe["id"])
                if self.operations.events else (),
            "operations": self._operation_records(),
            "actions": self._action_records(),
            "archive": self._archive_records(),
        }
        result["navigation"] = self.navigation_view()
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
            for resource_type, amount in (target.get("resources") or {}).items():
                rows.append(cls._resource_row(
                    "natural_deposit", target.get("name") or target.get("id", "Mineable object"),
                    resource_type, amount,
                    f"Remaining on {str(target.get('type', 'mineable object')).replace('_', ' ')} · {target.get('classification', 'observed')}",
                ))

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
            "sourceType": detail.split(" · ", 1)[0].removeprefix("Remaining on ").replace(" ", "_")
                if scope == "natural_deposit" else scope,
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
                "knowledgeLevel": sector.get("knowledgeLevel", "visited"),
                "confidence": float(sector.get("confidence", 0) or 0),
                "isFocused": coordinate.x == focus_coordinates.get("x") and coordinate.y == focus_coordinates.get("y") and coordinate.z == focus_coordinates.get("z"),
            })
        edges = []
        for index, source in enumerate(nodes):
            for target in nodes[index + 1:]:
                if max(abs(source[axis] - target[axis]) for axis in ("x", "y", "z")) == 1:
                    edges.append({"from": source["id"], "to": target["id"]})
        return {"nodes": tuple(nodes), "edges": tuple(edges), "sectorCount": len(nodes)}

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
    def _production(probe, mannies):
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
            operation = MissionControlViewModelBuilder._task_name(task_type, task)
            work.append({
                "id": str(manny.get("id", manny.get("name", len(work)))),
                "asset": manny.get("name", "Manny"),
                "taskType": task_type,
                "name": operation,
                "progress": progress,
                "eta": eta,
                "displayText": f"{manny.get('name', 'MANNY')} · {operation.upper()}    {progress:.0f}%",
                "detailText": MissionControlViewModelBuilder._task_details(
                    manny.get("name", "Manny"), task_type, task, progress, eta,
                ),
            })

        for item in probe.get("inventory", {}).get("items", ()):
            if item.get("type") != "atomic_3d_printer" or not item.get("currentTask"):
                continue
            task = item.get("task") if isinstance(item.get("task"), dict) else {}
            progress = float(item.get("taskProgressPercent", 0) or 0)
            eta = item.get("taskEstimatedEndTime") or "—"
            operation = MissionControlViewModelBuilder._task_name(item["currentTask"], task)
            work.append({
                "id": str(item.get("id", "atomic-printer")),
                "asset": item.get("name", "Atomic printer"),
                "taskType": item["currentTask"],
                "name": operation,
                "progress": progress,
                "eta": eta,
                "displayText": f"ATOMIC PRINTER · {operation.upper()}    {progress:.0f}%",
                "detailText": MissionControlViewModelBuilder._task_details(
                    item.get("name", "Atomic printer"), item["currentTask"], task,
                    progress, eta,
                ),
            })
        return tuple(work)

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
            lines.append(f"Target: {task.get('objectId') or target.get('name') or 'Unknown'}")
            lines.append(f"Trip: {task.get('tripIndex', '—')}")
            if task.get("targetAmount") is not None:
                lines.append(f"Target amount: {task['targetAmount']} ECE")
            if task.get("depositedAmount") is not None:
                lines.append(f"Deposited: {task['depositedAmount']} ECE")
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
