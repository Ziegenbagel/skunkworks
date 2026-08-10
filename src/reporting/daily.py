"""Generate one role-aware game-logbook report per probe and local day."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime, time, timedelta


TITLE_PREFIX = "Skunkworks Daily Report"


class DailyProbeReportService:
    """Build and publish the latest report due at 17:00 operator-local time."""

    def __init__(self, data_engine, now=None):
        self.data_engine = data_engine
        self._now = now or (lambda: datetime.now().astimezone())

    def generate_due(self, probes, roles, create_page):
        """Publish missing reports and return summaries of successful pages."""
        cutoff = self._latest_cutoff(self._now())
        start = cutoff - timedelta(days=1)
        role_map = {str(key): value for key, value in dict(roles or {}).items()}
        created = []
        failures = []
        for probe in probes:
            probe_id = int(probe["id"])
            marker = self.marker_key(probe_id, cutoff.date().isoformat())
            if self.data_engine.get_preference(marker) is not None:
                continue
            role = role_map.get(str(probe_id), "unassigned")
            title = f"{TITLE_PREFIX} · {cutoff.date().isoformat()}"
            try:
                content = self.build(probe, role, start, cutoff)
                response = create_page(
                    probe_id,
                    {"title": title[:120], "content": content[:20000]},
                )
            except Exception as error:  # API failures must not prevent app load.
                failures.append({"probeId": probe_id, "message": str(error)})
                continue
            page = response.get("page", response) if isinstance(response, dict) else {}
            page_id = page.get("id") if isinstance(page, dict) else None
            self.data_engine.set_preference(marker, str(page_id or "created"))
            self.data_engine.save_archive_report(
                f"daily:{probe_id}:{cutoff.date().isoformat()}",
                title,
                content,
                kind="daily_probe_report",
            )
            created.append({"probeId": probe_id, "pageId": page_id, "title": title})
        return {"created": created, "failures": failures}

    def build(self, probe, role, start, end):
        probe_id = int(probe["id"])
        actions = self._actions(probe_id, start, end)
        lines = [
            "SKUNKWORKS DAILY OPERATIONS REPORT",
            f"Probe: {probe.get('name') or f'Probe {probe_id}'}",
            f"Role: {self._role_name(role)}",
            f"Reporting window: {self._stamp(start)} to {self._stamp(end)}",
            "",
        ]
        lines.extend(self._role_summary(role, actions))
        if role == "explorer":
            lines.extend(self._explorer_summary(probe_id, start, end))
        lines.extend(self._common_summary(actions))
        lines.extend([
            "",
            "Data note: activity totals are based on commands accepted by the game and "
            "telemetry retained by Skunkworks. Survey quantities are the latest recorded "
            "amounts in this reporting window; unavailable telemetry is not inferred.",
            "Generated automatically by Skunkworks.",
        ])
        return "\n".join(lines)

    def annotate_page(self, page, probe_id):
        item = dict(page)
        date = self.report_date(item.get("title", ""))
        item["isDailyReport"] = date is not None
        item["isNewDailyReport"] = bool(
            date and self.data_engine.get_preference(self.read_key(probe_id, date), "false") != "true"
        )
        return item

    def mark_read(self, probe_id, title):
        date = self.report_date(title)
        if date:
            self.data_engine.set_preference(self.read_key(probe_id, date), "true")

    @staticmethod
    def report_date(title):
        prefix = f"{TITLE_PREFIX} · "
        return str(title)[len(prefix):].strip() if str(title).startswith(prefix) else None

    @staticmethod
    def marker_key(probe_id, report_date):
        return f"daily_report_generated:{int(probe_id)}:{report_date}"

    @staticmethod
    def read_key(probe_id, report_date):
        return f"daily_report_read:{int(probe_id)}:{report_date}"

    @staticmethod
    def _latest_cutoff(now):
        cutoff = datetime.combine(now.date(), time(17, 0), tzinfo=now.tzinfo)
        return cutoff if now >= cutoff else cutoff - timedelta(days=1)

    def _actions(self, probe_id, start, end):
        rows = self.data_engine._rows(
            """
            SELECT command_type, command_json, observed_at
            FROM action_journal
            WHERE probe_id = ? AND status = 'succeeded'
              AND observed_at > ? AND observed_at <= ?
            ORDER BY observed_at, id
            """,
            (probe_id, self._storage_stamp(start), self._storage_stamp(end)),
        )
        actions = []
        for row in rows:
            try:
                command = json.loads(row["command_json"])
            except (TypeError, ValueError, json.JSONDecodeError):
                command = {}
            actions.append({
                "type": row["command_type"],
                "command": command,
                "observedAt": row["observed_at"],
            })
        return actions

    def _role_summary(self, role, actions):
        types = Counter(item["type"] for item in actions)
        mining = [item for item in actions if item["type"] == "manny_mine" and not self._is_transfer(item)]
        transfers = [item for item in actions if self._is_transfer(item)]
        craft_actions = [item for item in actions if item["type"] in {
            "manny_craft", "atomic_printer_craft", "manny_assemble_probe"
        }]
        lines = ["ROLE ACTIVITY"]
        if role == "hub":
            lines.extend(self._craft_breakdown(craft_actions))
            lines.extend(self._mining_breakdown(mining))
            lines.extend(self._transfer_breakdown(transfers))
        elif role in {"transport", "deuterium_tanker", "deuterium_reserve"}:
            lines.extend(self._transfer_breakdown(transfers))
            lines.extend(self._mining_breakdown(mining))
            lines.extend(self._travel_breakdown(actions))
        elif role in {"miner", "builder_support"}:
            lines.extend(self._mining_breakdown(mining))
            lines.extend(self._craft_breakdown(craft_actions))
        elif role == "explorer":
            lines.extend(self._travel_breakdown(actions))
        else:
            lines += [f"- Skunkworks orders dispatched: {len(actions)}"]
        repairs = types["manny_repair"]
        if repairs:
            lines.append(f"- Repair orders dispatched: {repairs}")
        return lines + [""]

    def _explorer_summary(self, probe_id, start, end):
        history = self.data_engine._rows(
            """
            SELECT sector_x, sector_y, sector_z, observed_at
            FROM probe_state_history
            WHERE probe_id = ? AND observed_at > ? AND observed_at <= ?
              AND sector_x IS NOT NULL AND sector_y IS NOT NULL AND sector_z IS NOT NULL
            ORDER BY observed_at, id
            """,
            (probe_id, self._storage_stamp(start), self._storage_stamp(end)),
        )
        route = []
        for row in history:
            point = (row["sector_x"], row["sector_y"], row["sector_z"])
            if self._complete_point(point) and (not route or route[-1] != point):
                route.append(point)
        visited = set(route)
        observations = self.data_engine._rows(
            """
            SELECT sector_x, sector_y, sector_z, knowledge_level, confidence,
                   payload_json, observed_at
            FROM sector_observations
            WHERE probe_id = ? AND observed_at > ? AND observed_at <= ?
              AND knowledge_level = 'detailed'
            ORDER BY observed_at DESC, id DESC
            """,
            (probe_id, self._storage_stamp(start), self._storage_stamp(end)),
        )
        latest_sectors = {}
        for row in observations:
            point = (row["sector_x"], row["sector_y"], row["sector_z"])
            if not self._complete_point(point):
                continue
            if point not in visited:
                continue
            latest_sectors.setdefault(point, row)
        resources = self.data_engine._rows(
            """
            SELECT sector_x, sector_y, sector_z, object_id, classification,
                   resource_type, amount, composition, observed_at
            FROM resource_history
            WHERE probe_id = ? AND observed_at > ? AND observed_at <= ?
            ORDER BY observed_at DESC, id DESC
            """,
            (probe_id, self._storage_stamp(start), self._storage_stamp(end)),
        )
        latest_resources = {}
        for row in resources:
            point = (row["sector_x"], row["sector_y"], row["sector_z"])
            if not self._complete_point(point):
                continue
            if point not in visited:
                continue
            key = (row["sector_x"], row["sector_y"], row["sector_z"], row["object_id"], row["resource_type"])
            latest_resources.setdefault(key, row)
        by_sector = defaultdict(list)
        for row in latest_resources.values():
            by_sector[(row["sector_x"], row["sector_y"], row["sector_z"])].append(row)
        points = list(dict.fromkeys(route))
        lines = ["EXPLORATION SURVEY", f"- Sectors occupied or visited: {len(points)}"]
        if route:
            lines.append("- Recorded route: " + " → ".join(
                f"{point[0]}:{point[1]}:{point[2]}" for point in route
            ))
        if not points:
            return lines + ["- No visited-sector telemetry was retained in this window.", ""]
        for point in points:
            obs = latest_sectors.get(point)
            knowledge = (obs["knowledge_level"] if obs else None) or "recorded"
            confidence = obs["confidence"] if obs else None
            confidence_value = float(confidence) if confidence is not None else None
            if confidence_value is not None and confidence_value <= 1:
                confidence_value *= 100
            confidence_text = f", {confidence_value:.0f}% confidence" if confidence_value is not None else ""
            lines.append(f"\nSector {point[0]}:{point[1]}:{point[2]} — {knowledge}{confidence_text}")
            lines.extend(self._sector_details(obs))
            objects = defaultdict(list)
            for row in by_sector.get(point, ()):
                classification = row["classification"] or "resource object"
                if str(classification).lower() in {"persistent", "unknown", "object"}:
                    classification = "resource object"
                objects[(row["object_id"], classification)].append(row)
            totals = defaultdict(float)
            if not objects:
                lines.append("- No asteroid/resource quantities recorded.")
            for (object_id, classification), rows in sorted(objects.items()):
                values = []
                for row in sorted(rows, key=lambda item: item["resource_type"]):
                    amount = float(row["amount"] or 0)
                    if amount <= 0:
                        continue
                    totals[row["resource_type"]] += amount
                    values.append(f"{row['resource_type']}: {amount:.3f} ECE")
                if values:
                    lines.append(f"- {classification.title()} {object_id}: " + ", ".join(values))
            if totals:
                lines.append("- Sector resource total: " + ", ".join(
                    f"{resource}: {amount:.3f} ECE" for resource, amount in sorted(totals.items())
                ))
        return lines + [""]

    @staticmethod
    def _sector_details(observation):
        if not observation:
            return ["- Detailed sector telemetry unavailable."]
        try:
            payload = json.loads(observation["payload_json"] or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            return ["- Detailed sector telemetry could not be decoded."]
        sector = payload.get("sector", payload) if isinstance(payload, dict) else {}
        objects = sector.get("objects") or ()
        summaries = []
        for item in objects:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type") or item.get("classification") or "object").replace("_", " ")
            if kind.lower() in {"solar system", "solar_system"}:
                stars = item.get("starCount")
                planets = item.get("planetCount")
                orbitals = item.get("orbitalBodyCount")
                values = []
                if stars is not None:
                    values.append(f"{stars} star(s)")
                if planets is not None:
                    values.append(f"{planets} planet(s)")
                if orbitals is not None:
                    values.append(f"{orbitals} orbital object(s)")
                summaries.append("Solar system: " + (", ".join(values) or "details recorded"))
            else:
                summaries.append(str(item.get("summary") or item.get("name") or kind.title()))
        summary = sector.get("summary") if isinstance(sector, dict) else None
        if summary and summary not in summaries:
            summaries.insert(0, str(summary))
        if not summaries:
            return ["- Detailed scan recorded; no celestial objects reported."]
        return [f"- {value}" for value in summaries]

    @staticmethod
    def _common_summary(actions):
        counts = Counter(item["type"] for item in actions)
        labels = {
            "manny_mine": "Mining/transfer",
            "manny_craft": "Manny crafting",
            "atomic_printer_craft": "Atomic-printer crafting",
            "manny_assemble_probe": "Probe assembly",
            "manny_repair": "Repair",
            "move_probe": "Travel",
        }
        lines = ["ORDER AUDIT"]
        if not counts:
            lines.append("- No Skunkworks orders were accepted by the game in this window.")
        else:
            for command_type, count in sorted(counts.items()):
                lines.append(f"- {labels.get(command_type, command_type)} orders accepted: {count}")
        return lines

    @staticmethod
    def _is_transfer(item):
        return bool((item["command"].get("metadata") or {}).get("transportTransfer"))

    @staticmethod
    def _craft_breakdown(actions):
        recipes = Counter()
        for item in actions:
            command = item["command"]
            recipe = (command.get("payload") or {}).get("recipe")
            if item["type"] == "manny_assemble_probe":
                recipe = recipe or "probe assembly"
            recipes[str(recipe or "unknown recipe").replace("_", " ").title()] += 1
        if not recipes:
            return ["- Crafting/assembly: no orders dispatched."]
        return ["- Crafting/assembly orders dispatched:"] + [
            f"  - {recipe}: {count}" for recipe, count in sorted(recipes.items())
        ]

    @staticmethod
    def _mining_breakdown(actions):
        resources = defaultdict(lambda: {"orders": 0, "amount": 0.0, "objects": set()})
        for item in actions:
            command = item["command"]
            payload = command.get("payload") or {}
            metadata = command.get("metadata") or {}
            names = payload.get("resources") or (metadata.get("resource") or "unknown",)
            if isinstance(names, str):
                names = (names,)
            amount = metadata.get("orderAmount", payload.get("targetAmount", 0))
            for name in names:
                record = resources[str(name).replace("_", " ").title()]
                record["orders"] += 1
                record["amount"] += DailyProbeReportService._number(amount)
                if payload.get("objectId"):
                    record["objects"].add(str(payload["objectId"]))
        if not resources:
            return ["- Mining: no orders dispatched."]
        lines = ["- Mining orders dispatched:"]
        for resource, record in sorted(resources.items()):
            source = f" across {len(record['objects'])} source object(s)" if record["objects"] else ""
            lines.append(
                f"  - {resource}: {record['orders']} order(s), {record['amount']:.3f} ECE requested{source}"
            )
        return lines

    @staticmethod
    def _transfer_breakdown(actions):
        targets = defaultdict(lambda: {"orders": 0, "amount": 0.0})
        for item in actions:
            payload = item["command"].get("payload") or {}
            target = str(payload.get("targetProbeId") or "unknown probe")
            targets[target]["orders"] += 1
            targets[target]["amount"] += DailyProbeReportService._number(payload.get("amount"))
        if not targets:
            return ["- Deuterium transfers: no orders dispatched."]
        return ["- Deuterium transfer orders dispatched:"] + [
            f"  - To probe {target}: {record['orders']} order(s), {record['amount']:.3f} ECE requested"
            for target, record in sorted(targets.items())
        ]

    @staticmethod
    def _travel_breakdown(actions):
        destinations = []
        final_destination = None
        for item in actions:
            if item["type"] != "move_probe":
                continue
            command = item["command"]
            target = (command.get("payload") or {}).get("target") or {}
            if all(axis in target for axis in ("x", "y", "z")):
                destinations.append(f"{target['x']}:{target['y']}:{target['z']}")
            final = (command.get("metadata") or {}).get("finalDestination") or {}
            if all(axis in final for axis in ("x", "y", "z")):
                final_destination = f"{final['x']}:{final['y']}:{final['z']}"
        if not destinations:
            return ["- Travel: no legs dispatched."]
        lines = [f"- Travel legs dispatched: {len(destinations)}"]
        lines.append("  - Route: " + " → ".join(destinations))
        if final_destination:
            lines.append(f"  - Final destination: {final_destination}")
        return lines

    @staticmethod
    def _number(value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _amounts(actions, command_type, metadata_key, payload_key):
        values = []
        for item in actions:
            if item["type"] != command_type:
                continue
            command = item["command"]
            metadata = command.get("metadata") or {}
            payload = command.get("payload") or {}
            raw = metadata.get(metadata_key, payload.get(payload_key, 0))
            try:
                values.append(float(raw or 0))
            except (TypeError, ValueError):
                values.append(0.0)
        return values

    @staticmethod
    def _role_name(role):
        return str(role or "unassigned").replace("_", " ").title()

    @staticmethod
    def _stamp(value):
        return value.strftime("%Y-%m-%d %H:%M %Z")

    @staticmethod
    def _complete_point(point):
        return all(isinstance(value, int) and not isinstance(value, bool) for value in point)

    @staticmethod
    def _storage_stamp(value):
        return value.astimezone(UTC).isoformat()
