"""Versioned SQLite persistence for operational and historical data."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


SCHEMA_VERSION = 2


class DataEngine:
    """Persist application preferences and observable game history."""

    def __init__(self, path="data/skunkworks.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def set_preference(self, key, value):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, str(value), self._now()),
            )

    def get_preference(self, key, default=None):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM preferences WHERE key = ?",
                (key,),
            ).fetchone()

        return default if row is None else row["value"]

    def remember_probe(self, probe_id):
        self.set_preference("focused_probe_id", int(probe_id))

    def remembered_probe_id(self):
        value = self.get_preference("focused_probe_id")

        if value is None:
            return None

        try:
            return int(value)
        except ValueError:
            return None

    def record_world(self, world, observed_at=None):
        """Record normalized probe state and detailed sector resources."""

        observed_at = observed_at or self._now()
        probe = world.probe
        sector = probe.get("sector") or {}
        relative = sector.get("relative") or {}

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO probe_state_history (
                    probe_id, observed_at, name, model, status,
                    sector_x, sector_y, sector_z, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    probe["id"],
                    observed_at,
                    probe["name"],
                    probe.get("model", "generic"),
                    probe["status"],
                    relative.get("x"),
                    relative.get("y"),
                    relative.get("z"),
                    self._json(probe),
                ),
            )

            snapshot = world.sector.get("snapshot")

            if snapshot is not None:
                self._record_sector(
                    connection,
                    probe["id"],
                    snapshot,
                    observed_at,
                )

            for resource in world.sector.get(
                "resources",
                [],
            ):
                for resource_type, amount in resource.get(
                    "resources",
                    {},
                ).items():
                    connection.execute(
                        """
                        INSERT INTO resource_history (
                            probe_id, observed_at, sector_x,
                            sector_y, sector_z, object_id,
                            classification, resource_type,
                            amount, composition
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            probe["id"],
                            observed_at,
                            relative.get("x"),
                            relative.get("y"),
                            relative.get("z"),
                            resource["id"],
                            resource.get("classification"),
                            resource_type,
                            amount,
                            resource.get(
                                "composition",
                                {},
                            ).get(resource_type),
                        ),
                    )

    def sync_visits(self, payload, probe_id=None):
        """Upsert fleet-wide or per-probe visited-sector history."""

        scope = (
            "fleet"
            if probe_id is None
            else f"probe:{probe_id}"
        )

        with self._connect() as connection:
            for visit in payload.get("visitedSectors", []):
                coordinates = visit["relativeCoordinates"]
                connection.execute(
                    """
                    INSERT INTO sector_visits (
                        scope, probe_id, sector_x, sector_y,
                        sector_z, first_visited_at,
                        last_visited_at, visit_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(scope, sector_x, sector_y, sector_z)
                    DO UPDATE SET
                        first_visited_at = excluded.first_visited_at,
                        last_visited_at = excluded.last_visited_at,
                        visit_count = excluded.visit_count
                    """,
                    (
                        scope,
                        probe_id,
                        coordinates["x"],
                        coordinates["y"],
                        coordinates["z"],
                        visit.get("firstVisitedAt"),
                        visit.get("lastVisitedAt"),
                        visit.get("visitCount", 0),
                    ),
                )

    def record_records(
        self,
        domain,
        records,
        probe_id=None,
        observed_at=None,
    ):
        """Upsert messages, alerts, warnings, missions, or future events."""

        observed_at = observed_at or self._now()
        scope = (
            "account"
            if probe_id is None
            else f"probe:{probe_id}"
        )

        with self._connect() as connection:
            for record in records:
                external_id = str(
                    record.get("id")
                    or record.get("uid")
                    or self._json(record)
                )
                connection.execute(
                    """
                    INSERT INTO event_records (
                        domain, external_id, scope, probe_id,
                        observed_at, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(domain, external_id, scope)
                    DO UPDATE SET
                        observed_at = excluded.observed_at,
                        payload_json = excluded.payload_json
                    """,
                    (
                        domain,
                        external_id,
                        scope,
                        probe_id,
                        observed_at,
                        self._json(record),
                    ),
                )

    def probe_history(self, probe_id):
        return self._rows(
            """
            SELECT * FROM probe_state_history
            WHERE probe_id = ?
            ORDER BY observed_at
            """,
            (probe_id,),
        )

    def resource_history(
        self,
        resource_type=None,
        probe_id=None,
    ):
        conditions = []
        parameters = []

        if resource_type is not None:
            conditions.append("resource_type = ?")
            parameters.append(resource_type)

        if probe_id is not None:
            conditions.append("probe_id = ?")
            parameters.append(probe_id)

        where = (
            " WHERE " + " AND ".join(conditions)
            if conditions
            else ""
        )
        return self._rows(
            (
                "SELECT * FROM resource_history"
                f"{where} ORDER BY observed_at"
            ),
            tuple(parameters),
        )

    def visits(self, probe_id=None):
        scope = (
            "fleet"
            if probe_id is None
            else f"probe:{probe_id}"
        )
        return self._rows(
            """
            SELECT * FROM sector_visits
            WHERE scope = ?
            ORDER BY last_visited_at DESC
            """,
            (scope,),
        )

    def records(self, domain, probe_id=None):
        if probe_id is None:
            return self._rows(
                """
                SELECT * FROM event_records
                WHERE domain = ?
                ORDER BY observed_at DESC
                """,
                (domain,),
            )

        return self._rows(
            """
            SELECT * FROM event_records
            WHERE domain = ? AND probe_id = ?
            ORDER BY observed_at DESC
            """,
            (domain, probe_id),
        )

    def record_action(
        self,
        fingerprint,
        command,
        status,
        blockers=(),
        observed_at=None,
    ):
        """Append one immutable command lifecycle event."""

        observed_at = observed_at or self._now()

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO action_journal (
                    fingerprint, probe_id, command_type,
                    status, observed_at, command_json,
                    blockers_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fingerprint,
                    command["probeId"],
                    command["type"],
                    status,
                    observed_at,
                    self._json(command),
                    self._json(list(blockers)),
                ),
            )
            return cursor.lastrowid

    def action_history(self, probe_id=None):
        if probe_id is None:
            return self._rows(
                """
                SELECT * FROM action_journal
                ORDER BY id
                """,
                (),
            )

        return self._rows(
            """
            SELECT * FROM action_journal
            WHERE probe_id = ?
            ORDER BY id
            """,
            (probe_id,),
        )

    def action_was_successful(self, fingerprint):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1 FROM action_journal
                WHERE fingerprint = ? AND status = 'succeeded'
                LIMIT 1
                """,
                (fingerprint,),
            ).fetchone()

        return row is not None

    def galaxy_map(self):
        """Rebuild the in-memory map from durable visit and observation data."""

        from src.intelligence.galaxy import GalaxyMapBuilder

        fleet_history = {
            "visitedSectors": [
                self._visit_payload(row)
                for row in self.visits()
            ]
        }
        probe_histories = {}

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM sector_visits
                WHERE probe_id IS NOT NULL
                ORDER BY probe_id, last_visited_at
                """
            ).fetchall()

            for row in rows:
                probe_histories.setdefault(
                    row["probe_id"],
                    {"visitedSectors": []},
                )["visitedSectors"].append(
                    self._visit_payload(row)
                )

            observations = connection.execute(
                """
                SELECT * FROM sector_observations
                ORDER BY observed_at DESC
                """
            ).fetchall()

        galaxy = GalaxyMapBuilder().build(
            fleet_history,
            probe_histories,
        )
        seen = set()

        for row in observations:
            coordinates = (
                row["sector_x"],
                row["sector_y"],
                row["sector_z"],
            )

            if coordinates in seen:
                continue

            seen.add(coordinates)
            galaxy.record_observation(
                json.loads(row["payload_json"]),
                probe_id=row["probe_id"],
            )

        return galaxy

    def schema_version(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT MAX(version) AS version FROM schema_migrations"
            ).fetchone()
        return int(row["version"] or 0)

    def _record_sector(
        self,
        connection,
        probe_id,
        snapshot,
        observed_at,
    ):
        sector = snapshot["sector"]
        coordinates = sector["relativeCoordinates"]
        connection.execute(
            """
            INSERT INTO sector_observations (
                probe_id, observed_at, sector_x, sector_y,
                sector_z, knowledge_level, confidence, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                probe_id,
                observed_at,
                coordinates["x"],
                coordinates["y"],
                coordinates["z"],
                sector.get("knowledgeLevel"),
                sector.get("confidence"),
                self._json(snapshot),
            ),
        )

    def _migrate(self):
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS probe_state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    probe_id INTEGER NOT NULL,
                    observed_at TEXT NOT NULL,
                    name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    status TEXT NOT NULL,
                    sector_x INTEGER,
                    sector_y INTEGER,
                    sector_z INTEGER,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS
                    idx_probe_history_probe_time
                ON probe_state_history(probe_id, observed_at);

                CREATE TABLE IF NOT EXISTS sector_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    probe_id INTEGER NOT NULL,
                    observed_at TEXT NOT NULL,
                    sector_x INTEGER NOT NULL,
                    sector_y INTEGER NOT NULL,
                    sector_z INTEGER NOT NULL,
                    knowledge_level TEXT,
                    confidence REAL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS
                    idx_sector_observations_coordinates_time
                ON sector_observations(
                    sector_x, sector_y, sector_z, observed_at
                );

                CREATE TABLE IF NOT EXISTS resource_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    probe_id INTEGER NOT NULL,
                    observed_at TEXT NOT NULL,
                    sector_x INTEGER,
                    sector_y INTEGER,
                    sector_z INTEGER,
                    object_id TEXT NOT NULL,
                    classification TEXT,
                    resource_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    composition REAL
                );

                CREATE INDEX IF NOT EXISTS
                    idx_resource_history_type_time
                ON resource_history(resource_type, observed_at);

                CREATE TABLE IF NOT EXISTS sector_visits (
                    scope TEXT NOT NULL,
                    probe_id INTEGER,
                    sector_x INTEGER NOT NULL,
                    sector_y INTEGER NOT NULL,
                    sector_z INTEGER NOT NULL,
                    first_visited_at TEXT,
                    last_visited_at TEXT,
                    visit_count INTEGER NOT NULL,
                    PRIMARY KEY (
                        scope, sector_x, sector_y, sector_z
                    )
                );

                CREATE TABLE IF NOT EXISTS event_records (
                    domain TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    probe_id INTEGER,
                    observed_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (domain, external_id, scope)
                );

                CREATE TABLE IF NOT EXISTS action_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fingerprint TEXT NOT NULL,
                    probe_id INTEGER NOT NULL,
                    command_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    command_json TEXT NOT NULL,
                    blockers_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS
                    idx_action_journal_fingerprint_status
                ON action_journal(fingerprint, status);

                CREATE INDEX IF NOT EXISTS
                    idx_action_journal_probe_time
                ON action_journal(probe_id, observed_at);
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (
                    version, applied_at
                ) VALUES (?, ?)
                """,
                (SCHEMA_VERSION, self._now()),
            )

    def _rows(self, query, parameters):
        with self._connect() as connection:
            return connection.execute(
                query,
                parameters,
            ).fetchall()

    def _visit_payload(self, row):
        return {
            "relativeCoordinates": {
                "x": row["sector_x"],
                "y": row["sector_y"],
                "z": row["sector_z"],
            },
            "firstVisitedAt": row["first_visited_at"],
            "lastVisitedAt": row["last_visited_at"],
            "visitCount": row["visit_count"],
        }

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")

        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _json(self, value):
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        )

    def _now(self):
        return datetime.now(UTC).isoformat()
