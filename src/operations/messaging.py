"""Unified, durable player communication workflows."""

import json
import re

from src.models.galaxy import SectorCoordinates


class MessagingService:
    COORDINATES = re.compile(
        r"(?<!\d)(-?\d+)\s*[,/]\s*(-?\d+)\s*[,/]\s*(-?\d+)(?!\d)"
    )

    def __init__(self, data_engine, capabilities=None):
        self.data_engine = data_engine
        self.capabilities = capabilities

    def inbox(self, probe_id=None, unread_only=False):
        messages = self._payloads("messages", probe_id)
        if unread_only:
            messages = tuple(
                item for item in messages
                if not item.get("read", item.get("isRead", False))
            )
        return messages

    def outbox(self):
        return self._payloads("sent_messages")

    def send(self, probe_id, payload):
        if self.capabilities is None:
            raise RuntimeError("Live messaging capability is unavailable.")
        return self.capabilities.messaging.send(probe_id, payload)

    def mark_read(self, probe_id, message_id):
        if self.capabilities is None:
            raise RuntimeError("Live messaging capability is unavailable.")
        return self.capabilities.messaging.mark_read(probe_id, message_id)

    def extract_coordinates(self, message):
        text = " ".join(
            str(message.get(key, ""))
            for key in ("subject", "title", "body", "content")
        )
        coordinates = []
        for match in self.COORDINATES.finditer(text):
            try:
                value = SectorCoordinates(*(int(part) for part in match.groups()))
            except ValueError:
                continue
            if value not in coordinates:
                coordinates.append(value)
        return tuple(coordinates)

    def _payloads(self, domain, probe_id=None):
        return tuple(
            json.loads(row["payload_json"])
            for row in self.data_engine.records(domain, probe_id)
        )


class MissionService:
    def __init__(self, data_engine, capabilities=None):
        self.data_engine = data_engine
        self.capabilities = capabilities

    def all(self):
        return tuple(
            json.loads(row["payload_json"])
            for row in self.data_engine.records("missions")
        )

    def current(self):
        return next(
            (
                mission for mission in self.all()
                if mission.get("status") in {"active", "accepted", "in_progress"}
            ),
            None,
        )

    def progress(self, mission):
        return mission.get("progress", mission.get("progressPercent", 0))

    def abandon(self, mission_id, *, confirmed=False):
        if not confirmed:
            raise PermissionError("Mission abandonment requires confirmation.")
        if self.capabilities is None:
            raise RuntimeError("Live mission capability is unavailable.")
        return self.capabilities.missions.abandon(mission_id)


class EventService:
    DOMAINS = (
        "messages", "sent_messages", "alerts", "damage_warnings",
        "missions", "logbook_pages",
    )

    def __init__(self, data_engine):
        self.data_engine = data_engine

    def timeline(self, probe_id=None):
        events = []
        for domain in self.DOMAINS:
            for row in self.data_engine.records(domain, probe_id):
                state = self.data_engine.event_state(domain, row["external_id"])
                events.append(
                    {
                        "domain": domain,
                        "id": row["external_id"],
                        "observedAt": row["observed_at"],
                        "payload": json.loads(row["payload_json"]),
                        "acknowledged": bool(state["acknowledged"]) if state else False,
                        "priority": state["priority"] if state else "normal",
                        "linkedOperationId": state["linked_operation_id"] if state else None,
                    }
                )
        return tuple(
            sorted(
                events,
                key=lambda item: (
                    {"urgent": 2, "high": 1}.get(item["priority"], 0),
                    item["observedAt"],
                ),
                reverse=True,
            )
        )

    def classify(
        self, domain, external_id, *, acknowledged=False,
        priority="normal", linked_operation_id=None,
    ):
        if priority not in {"normal", "high", "urgent"}:
            raise ValueError(f"Unknown event priority: {priority}")
        self.data_engine.set_event_state(
            domain, external_id, acknowledged=acknowledged,
            priority=priority, linked_operation_id=linked_operation_id,
        )
