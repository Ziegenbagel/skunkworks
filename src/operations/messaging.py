"""Unified, durable player communication workflows."""

import json
import math
import re
from datetime import datetime

from src.models.galaxy import SectorCoordinates


class MessagingService:
    COORDINATES = re.compile(
        r"(?<!\d)(-?\d+)\s*[,/]\s*(-?\d+)\s*[,/]\s*(-?\d+)(?!\d)"
    )
    ORACLE_DIRECTION = re.compile(
        r"(?:normalized\s+)?direction(?:\s+vector)?[^-+\d]*"
        r"[\[(]?\s*(-?\d+(?:\.\d+)?)\s*[,/ ]+\s*"
        r"(-?\d+(?:\.\d+)?)\s*[,/ ]+\s*(-?\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    ORACLE_DISTANCE = re.compile(
        r"(?:fcc\s+)?distance[^\d]*(\d+(?:\.\d+)?)", re.IGNORECASE,
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

    def oracle_contacts(self):
        """Derive the newest approximate Oracle fix for each queried player."""

        sent = sorted(self.outbox(), key=self._message_time)
        replies = sorted(self.inbox(), key=self._message_time)
        contacts = {}
        for reply in replies:
            sender = reply.get("sender") or {}
            if str(sender.get("type", "")).casefold() != "planet":
                continue
            parsed = self._oracle_measurement(reply)
            if parsed is None:
                continue
            planet_id = str(sender.get("id") or sender.get("planetId") or "")
            reply_time = self._message_time(reply)
            request = next((
                message for message in reversed(sent)
                if self._recipient_planet_id(message) == planet_id
                and self._message_time(message) <= reply_time
                and self._message_sector(message) is not None
                and str(message.get("body") or message.get("content") or "").strip()
            ), None)
            if request is None:
                continue
            player_name = str(request.get("body") or request.get("content")).strip()
            # Oracle queries are exact usernames, not prose messages.
            if "\n" in player_name or len(player_name) > 80:
                continue
            origin = self._message_sector(request)
            direction, distance = parsed
            estimate = self._estimate_fcc(origin, direction, distance)
            key = player_name.casefold()
            contacts[key] = {
                "id": f"oracle:{key}",
                "playerName": player_name,
                "label": f"Possible location · {player_name}",
                "x": estimate.x, "y": estimate.y, "z": estimate.z,
                "origin": {"x": origin.x, "y": origin.y, "z": origin.z},
                "direction": {"x": direction[0], "y": direction[1], "z": direction[2]},
                "distance": distance,
                "updatedAt": reply.get("createdAt") or reply.get("sentAt") or "",
                "replyMessageId": str(reply.get("id") or ""),
                "approximate": True,
                "mapState": "oracle_estimate",
                "visitCount": 0, "objectCount": 0, "objectTypes": (),
                "objects": (), "probeIds": (), "resourceTypes": (),
                "knowledgeLevel": "approximate intelligence",
                "confidence": 0, "hasHazard": False,
                "hasDetachedContainers": False, "hasHabitablePlanet": False,
            }
        return tuple(contacts.values())

    @classmethod
    def _oracle_measurement(cls, message):
        body = str(message.get("body") or message.get("content") or "")
        vector = cls.ORACLE_DIRECTION.search(body)
        distance = cls.ORACLE_DISTANCE.search(body)
        if not vector or not distance:
            return None
        direction = tuple(float(value) for value in vector.groups())
        magnitude = math.sqrt(sum(value * value for value in direction))
        if magnitude == 0:
            return None
        return tuple(value / magnitude for value in direction), float(distance.group(1))

    @staticmethod
    def _recipient_planet_id(message):
        recipient = message.get("recipient") or {}
        if str(recipient.get("type", "")).casefold() != "planet":
            return ""
        return str(recipient.get("id") or recipient.get("planetId") or "")

    @staticmethod
    def _message_sector(message):
        sector = message.get("sector") or {}
        relative = sector.get("relative") or sector.get("relativeCoordinates") or sector
        try:
            return SectorCoordinates.from_api(relative)
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _message_time(message):
        value = message.get("createdAt") or message.get("sentAt") or message.get("receivedAt") or ""
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _estimate_fcc(origin, direction, distance):
        raw = tuple(getattr(origin, axis) + direction[index] * distance for index, axis in enumerate(("x", "y", "z")))
        rounded = tuple(round(value) for value in raw)
        candidates = []
        for x in range(rounded[0] - 2, rounded[0] + 3):
            for y in range(rounded[1] - 2, rounded[1] + 3):
                for z in range(rounded[2] - 2, rounded[2] + 3):
                    if (x + y + z) % 2:
                        continue
                    point = SectorCoordinates(x, y, z)
                    distance_error = abs(origin.distance_to(point) - distance)
                    euclidean_error = sum((value - actual) ** 2 for value, actual in zip((x, y, z), raw))
                    candidates.append((distance_error, euclidean_error, point))
        return min(candidates, key=lambda item: (item[0], item[1]))[2]

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
