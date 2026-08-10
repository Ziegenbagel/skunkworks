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
            actions.append({"type": row["command_type"], "command": command})
        return actions

    def _role_summary(self, role, actions):
        types = Counter(item["type"] for item in actions)
        mined = self._amounts(actions, "manny_mine", "orderAmount", "targetAmount")
        transferred = self._amounts(
            [item for item in actions if (item["command"].get("metadata") or {}).get("transportTransfer")],
            "manny_mine", "orderAmount", "targetAmount",
        )
        lines = ["ROLE SUMMARY"]
        if role == "hub":
            lines += [
                f"- Crafting/assembly orders accepted: {types['manny_craft'] + types['atomic_printer_craft'] + types['manny_assemble_probe']}",
                f"- Transport transfer orders received/dispatched: {len(transferred)}",
            ]
        elif role in {"transport", "deuterium_tanker", "deuterium_reserve"}:
            lines += [
                f"- Transfer orders accepted: {len(transferred)}",
                f"- Transfer amount requested: {sum(transferred):.3f} ECE",
                f"- Travel legs accepted: {types['move_probe']}",
            ]
        elif role in {"miner", "builder_support"}:
            lines += [
                f"- Mining orders accepted: {len(mined)}",
                f"- Mining amount requested: {sum(mined):.3f} ECE",
                f"- Crafting/assembly orders accepted: {types['manny_craft'] + types['atomic_printer_craft'] + types['manny_assemble_probe']}",
            ]
        elif role == "explorer":
            lines += [f"- Travel legs accepted: {types['move_probe']}"]
        else:
            lines += [f"- Accepted Skunkworks commands: {len(actions)}"]
        return lines + [""]

    def _explorer_summary(self, probe_id, start, end):
        observations = self.data_engine._rows(
            """
            SELECT sector_x, sector_y, sector_z, knowledge_level, confidence, observed_at
            FROM sector_observations
            WHERE probe_id = ? AND observed_at > ? AND observed_at <= ?
            ORDER BY observed_at DESC, id DESC
            """,
            (probe_id, self._storage_stamp(start), self._storage_stamp(end)),
        )
        latest_sectors = {}
        incomplete_observations = 0
        for row in observations:
            point = (row["sector_x"], row["sector_y"], row["sector_z"])
            if not self._complete_point(point):
                incomplete_observations += 1
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
        incomplete_resources = 0
        for row in resources:
            point = (row["sector_x"], row["sector_y"], row["sector_z"])
            if not self._complete_point(point):
                incomplete_resources += 1
                continue
            key = (row["sector_x"], row["sector_y"], row["sector_z"], row["object_id"], row["resource_type"])
            latest_resources.setdefault(key, row)
        by_sector = defaultdict(list)
        for row in latest_resources.values():
            by_sector[(row["sector_x"], row["sector_y"], row["sector_z"])].append(row)
        points = sorted(set(latest_sectors) | set(by_sector))
        lines = ["EXPLORATION SURVEY", f"- Sectors scanned or surveyed: {len(points)}"]
        incomplete = incomplete_observations + incomplete_resources
        if incomplete:
            lines.append(
                f"- Telemetry records without sector coordinates omitted: {incomplete}"
            )
        if not points:
            return lines + ["- No sector survey telemetry was retained in this window.", ""]
        for point in points:
            obs = latest_sectors.get(point)
            knowledge = (obs["knowledge_level"] if obs else None) or "recorded"
            confidence = obs["confidence"] if obs else None
            confidence_text = f", {float(confidence):.0f}% confidence" if confidence is not None else ""
            lines.append(f"\nSector {point[0]}:{point[1]}:{point[2]} — {knowledge}{confidence_text}")
            objects = defaultdict(list)
            for row in by_sector.get(point, ()):
                objects[(row["object_id"], row["classification"] or "object")].append(row)
            totals = defaultdict(float)
            if not objects:
                lines.append("- No asteroid/resource quantities recorded.")
            for (object_id, classification), rows in sorted(objects.items()):
                values = []
                for row in sorted(rows, key=lambda item: item["resource_type"]):
                    amount = float(row["amount"] or 0)
                    totals[row["resource_type"]] += amount
                    values.append(f"{row['resource_type']}: {amount:.3f} ECE")
                lines.append(f"- {classification.title()} {object_id}: " + ", ".join(values))
            if totals:
                lines.append("- Sector resource total: " + ", ".join(
                    f"{resource}: {amount:.3f} ECE" for resource, amount in sorted(totals.items())
                ))
        return lines + [""]

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
        lines = ["ACTIVITY LEDGER"]
        if not counts:
            lines.append("- No accepted Skunkworks commands recorded in this window.")
        else:
            for command_type, count in sorted(counts.items()):
                lines.append(f"- {labels.get(command_type, command_type)}: {count}")
        return lines

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
