"""Versioned SQLite persistence for operational and historical data."""

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path


SCHEMA_VERSION = 4


class DataEngine:
    """Persist application preferences and observable game history."""

    # Refresh and automation workers create separate DataEngine instances in
    # one process. Share the last persisted sector/resource signature so each
    # worker does not append the same large snapshot again.
    _shared_world_history_signatures = {}

    def __init__(self, path="data/skunkworks.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._galaxy_cache = None
        self._galaxy_cache_built_at = 0.0
        # WAL mode is persistent database state. Configuring it on every
        # short-lived read connection takes a write lock and turns otherwise
        # tiny preference/history lookups into multi-second stalls when the UI
        # and automation workers are both active.
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA journal_mode = WAL")
        self._migrate()
        self.run_due_maintenance()

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
        coordinates = (
            relative.get("x"),
            relative.get("y"),
            relative.get("z"),
        )
        sector_changed = False
        snapshot = world.sector.get("snapshot")
        history_signature = self._world_history_signature(snapshot, world.sector)
        history_key = (str(self.path.resolve()), int(probe["id"]), coordinates)
        signature_preference = "world_history_signature:{}:{}:{}:{}".format(
            probe["id"], *coordinates,
        )
        persisted_signature = self.get_preference(signature_preference)
        persist_sector_history = (
            history_signature is not None
            and self._shared_world_history_signatures.get(history_key)
            != history_signature
            and persisted_signature != history_signature
        )
        probe_payload = self._json(self._probe_history_payload(probe))

        with self._connect() as connection:
            previous = connection.execute(
                """
                SELECT sector_x, sector_y, sector_z
                FROM probe_state_history
                WHERE probe_id = ?
                ORDER BY observed_at DESC, id DESC
                LIMIT 1
                """,
                (probe["id"],),
            ).fetchone()
            sector_changed = (
                None not in coordinates
                and (
                    previous is None
                    or tuple(previous) != coordinates
                )
            )
            previous_payload = connection.execute(
                """
                SELECT payload_json FROM probe_state_history
                WHERE probe_id = ?
                ORDER BY observed_at DESC, id DESC
                LIMIT 1
                """,
                (probe["id"],),
            ).fetchone()
            if previous_payload is None or previous_payload["payload_json"] != probe_payload:
                connection.execute(
                    """
                    INSERT INTO probe_state_history (
                        probe_id, observed_at, name, model, status,
                        sector_x, sector_y, sector_z, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        probe["id"], observed_at, probe["name"],
                        probe.get("model", "generic"), probe["status"],
                        relative.get("x"), relative.get("y"),
                        relative.get("z"), probe_payload,
                    ),
                )

            if snapshot is not None and persist_sector_history:
                self._record_sector(
                    connection,
                    probe["id"],
                    snapshot,
                    observed_at,
                )

            for resource in (
                world.sector.get("resources", [])
                if persist_sector_history else ()
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
            if persist_sector_history:
                connection.execute(
                    """
                    INSERT INTO preferences (key, value, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = excluded.updated_at
                    """,
                    (signature_preference, history_signature, observed_at),
                )

        if sector_changed:
            self._invalidate_galaxy_cache()
        if persist_sector_history:
            self._shared_world_history_signatures[history_key] = history_signature

    def _world_history_signature(self, snapshot, sector):
        """Return the material sector state, excluding refresh-only metadata."""

        if snapshot is None:
            return None
        resources = tuple(sorted(
            (
                str(item.get("id")),
                str(item.get("classification", "")),
                self._json(item.get("resources", {})),
                self._json(item.get("composition", {})),
            )
            for item in sector.get("resources", ())
        ))
        observed_sector = snapshot.get("sector", snapshot)
        objects = tuple(sorted(
            self._json(item)
            for item in observed_sector.get("objects", ())
        ))
        return self._json({
            "coordinates": observed_sector.get("relativeCoordinates", {}),
            "knowledgeLevel": observed_sector.get("knowledgeLevel"),
            "confidence": observed_sector.get("confidence"),
            "objects": objects,
            "resources": resources,
        })

    @staticmethod
    def _probe_history_payload(probe):
        """Keep route/status history without copying live inventory payloads."""

        sector = probe.get("sector") or {}
        relative = sector.get("relative") or sector.get("relativeCoordinates") or {}
        return {
            "id": probe.get("id"),
            "name": probe.get("name"),
            "model": probe.get("model", "generic"),
            "status": probe.get("status"),
            "sector": {"relative": {
                "x": relative.get("x"),
                "y": relative.get("y"),
                "z": relative.get("z"),
            }},
        }

    def record_sector_observation(self, probe_id, observation, observed_at=None):
        """Persist one explicit galaxy-map scan for later cartography."""

        snapshot = observation if "sector" in observation else {"sector": observation}
        with self._connect() as connection:
            self._record_sector(
                connection,
                probe_id,
                snapshot,
                observed_at or self._now(),
            )
        self._invalidate_galaxy_cache()

    def sync_visits(self, payload, probe_id=None):
        """Upsert fleet-wide or per-probe visited-sector history."""

        scope = (
            "fleet"
            if probe_id is None
            else f"probe:{probe_id}"
        )

        changed = False
        with self._connect() as connection:
            for visit in payload.get("visitedSectors", []):
                coordinates = visit["relativeCoordinates"]
                existing = connection.execute(
                    """
                    SELECT first_visited_at, last_visited_at, visit_count
                    FROM sector_visits
                    WHERE scope = ? AND sector_x = ? AND sector_y = ? AND sector_z = ?
                    """,
                    (scope, coordinates["x"], coordinates["y"], coordinates["z"]),
                ).fetchone()
                incoming = (
                    visit.get("firstVisitedAt"),
                    visit.get("lastVisitedAt"),
                    visit.get("visitCount", 0),
                )
                if existing is not None and tuple(existing) == incoming:
                    continue
                changed = True
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
        if changed:
            self._invalidate_galaxy_cache()

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

    def resource_source_history(
        self,
        coordinates,
        object_id,
        resource_type,
    ):
        return self._rows(
            """
            SELECT * FROM resource_history
            WHERE sector_x = ? AND sector_y = ? AND sector_z = ?
              AND object_id = ? AND resource_type = ?
            ORDER BY observed_at
            """,
            (
                coordinates.x,
                coordinates.y,
                coordinates.z,
                object_id,
                resource_type,
            ),
        )

    def latest_resource_sources(
        self,
        resource_type,
        minimum_amount=0,
    ):
        return self._rows(
            """
            WITH ranked AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY sector_x, sector_y,
                            sector_z, object_id, resource_type
                        ORDER BY observed_at DESC, id DESC
                    ) AS rank
                FROM resource_history
                WHERE resource_type = ?
                  AND sector_x IS NOT NULL
                  AND sector_y IS NOT NULL
                  AND sector_z IS NOT NULL
            )
            SELECT * FROM ranked
            WHERE rank = 1 AND amount >= ?
            ORDER BY amount DESC
            """,
            (resource_type, minimum_amount),
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

    def probe_route(self, probe_id, limit=10):
        """Return the probe's true chronological sector path.

        Unlike the visited-sector summary, state history retains revisits and
        therefore cannot accidentally draw another apparent route when a probe
        returns through a previously visited sector.
        """
        rows = self._rows(
            """
            SELECT observed_at, sector_x, sector_y, sector_z
            FROM probe_state_history
            WHERE probe_id = ?
              AND sector_x IS NOT NULL
              AND sector_y IS NOT NULL
              AND sector_z IS NOT NULL
            ORDER BY observed_at DESC, id DESC
            """,
            (probe_id,),
        )
        route = []
        for row in rows:
            point = (row["sector_x"], row["sector_y"], row["sector_z"])
            if route and route[-1]["point"] == point:
                continue
            route.append({"point": point, "observed_at": row["observed_at"]})
            if len(route) >= int(limit):
                break
        return tuple(route)

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

    def delete_record(self, domain, external_id, probe_id=None):
        """Remove one synchronized event after the game deletes it."""

        with self._connect() as connection:
            if probe_id is None:
                connection.execute(
                    "DELETE FROM event_records WHERE domain = ? AND external_id = ?",
                    (domain, str(external_id)),
                )
            else:
                connection.execute(
                    """
                    DELETE FROM event_records
                    WHERE domain = ? AND external_id = ? AND probe_id = ?
                    """,
                    (domain, str(external_id), int(probe_id)),
                )
            connection.execute(
                "DELETE FROM event_state WHERE domain = ? AND external_id = ?",
                (domain, str(external_id)),
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

    def recent_successful_actions(self, probe_id, limit=500):
        """Return only recent successful commands needed for live task labels."""

        return self._rows(
            """
            SELECT * FROM action_journal
            WHERE probe_id = ? AND status = 'succeeded'
            ORDER BY observed_at DESC, id DESC
            LIMIT ?
            """,
            (int(probe_id), max(1, int(limit))),
        )

    def compact_history(self, retain_high_resolution_days=30, *, vacuum=False):
        """Downsample old telemetry while preserving every current state.

        Recent telemetry remains untouched. Older probe and resource history
        retains one sample per UTC day, while sector observations retain the
        latest knowledge for every probe/coordinate pair. Operational records,
        preferences, action history, reports, and visits are never removed.
        """

        cutoff = (datetime.now(UTC) - timedelta(
            days=max(1, int(retain_high_resolution_days)),
        )).isoformat()
        with self._connect() as connection:
            before = connection.execute(
                "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
            ).fetchone()[0]
            connection.execute(
                """
                DELETE FROM probe_state_history
                WHERE observed_at < ? AND id NOT IN (
                    SELECT MAX(id) FROM probe_state_history
                    WHERE observed_at < ?
                    GROUP BY probe_id, substr(observed_at, 1, 10)
                )
                """,
                (cutoff, cutoff),
            )
            probe_rows = connection.execute("SELECT changes()").fetchone()[0]
            # Historical consumers use the indexed identity/status/coordinate
            # columns. Older builds copied the entire live probe payload here,
            # including large inventory structures, once per refresh.
            connection.execute(
                """
                UPDATE probe_state_history
                SET payload_json = json_object(
                    'id', probe_id,
                    'name', name,
                    'model', model,
                    'status', status,
                    'sector', json_object(
                        'relative', json_object(
                            'x', sector_x, 'y', sector_y, 'z', sector_z
                        )
                    )
                )
                WHERE length(payload_json) > 1024
                """
            )
            connection.execute(
                """
                DELETE FROM resource_history
                WHERE observed_at < ? AND id NOT IN (
                    SELECT MAX(id) FROM resource_history
                    WHERE observed_at < ?
                    GROUP BY probe_id, sector_x, sector_y, sector_z,
                             object_id, resource_type, substr(observed_at, 1, 10)
                )
                """,
                (cutoff, cutoff),
            )
            resource_rows = connection.execute("SELECT changes()").fetchone()[0]
            # Sector payloads are complete observations, often hundreds of
            # kilobytes each. Cartography needs the latest payload for each
            # probe/coordinate pair, not one duplicate payload per refresh.
            # Resource history remains separately downsampled above.
            connection.execute(
                """
                DELETE FROM sector_observations
                WHERE id NOT IN (
                    SELECT MAX(id) FROM sector_observations
                    GROUP BY probe_id, sector_x, sector_y, sector_z
                )
                """
            )
            sector_rows = connection.execute("SELECT changes()").fetchone()[0]
        if vacuum:
            with sqlite3.connect(self.path) as connection:
                connection.execute("VACUUM")
        with self._connect() as connection:
            after = connection.execute(
                "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
            ).fetchone()[0]
        self._invalidate_galaxy_cache()
        return {
            "probeRowsRemoved": int(probe_rows),
            "resourceRowsRemoved": int(resource_rows),
            "sectorRowsRemoved": int(sector_rows),
            "databaseBytesBefore": int(before),
            "databaseBytesAfter": int(after),
            "vacuumed": bool(vacuum),
        }

    def run_due_maintenance(self, interval_days=7):
        """Downsample history at most weekly without an exclusive vacuum.

        DataEngine instances are short lived and may be created by multiple
        workers. Claim the maintenance window in preferences before doing the
        work so only the first instance pays the bounded startup cost.
        """

        key = "last_history_compaction_at"
        now = datetime.now(UTC)
        interval = timedelta(days=max(1, int(interval_days)))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT value FROM preferences WHERE key = ?", (key,),
            ).fetchone()
            if row:
                try:
                    if now - datetime.fromisoformat(row["value"]) < interval:
                        return None
                except ValueError:
                    pass
            connection.execute(
                """
                INSERT INTO preferences (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, now.isoformat(), now.isoformat()),
            )
        return self.compact_history()

    def integrity_report(self):
        """Return non-mutating SQLite integrity and foreign-key results."""

        with self._connect() as connection:
            quick_check = tuple(
                row[0] for row in connection.execute("PRAGMA quick_check")
            )
            foreign_key_errors = tuple(
                dict(row) for row in connection.execute("PRAGMA foreign_key_check")
            )
        return {
            "ok": quick_check == ("ok",) and not foreign_key_errors,
            "quickCheck": quick_check,
            "foreignKeyErrors": foreign_key_errors,
        }

    def database_report(self):
        """Describe database allocation, sidecar files, and retained rows."""

        with self._connect() as connection:
            page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
            page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
            free_pages = int(connection.execute("PRAGMA freelist_count").fetchone()[0])
            tables = tuple(
                row[0]
                for row in connection.execute(
                    """
                    SELECT name FROM sqlite_schema
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                )
            )
            row_counts = {
                table: int(connection.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0])
                for table in tables
            }

        files = {}
        for label, path in (
            ("database", self.path),
            ("wal", Path(f"{self.path}-wal")),
            ("sharedMemory", Path(f"{self.path}-shm")),
        ):
            files[label] = path.stat().st_size if path.exists() else 0
        return {
            "schemaVersion": self.schema_version(),
            "pageSize": page_size,
            "pageCount": page_count,
            "allocatedBytes": page_size * page_count,
            "reclaimableBytes": page_size * free_pages,
            "files": files,
            "totalFileBytes": sum(files.values()),
            "rowCounts": row_counts,
        }

    def backup(self, destination, *, overwrite=False):
        """Create and verify a consistent online SQLite backup.

        SQLite's backup API includes committed WAL content, so callers do not
        need to stop refresh workers or copy sidecar files themselves.
        """

        destination = Path(destination)
        if destination.resolve() == self.path.resolve():
            raise ValueError("Backup destination must differ from the live database.")
        if destination.exists() and not overwrite:
            raise FileExistsError(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.partial")
        if temporary.exists():
            temporary.unlink()
        try:
            with self._connect() as source, sqlite3.connect(temporary) as target:
                source.backup(target)
                result = tuple(row[0] for row in target.execute("PRAGMA quick_check"))
                if result != ("ok",):
                    raise sqlite3.DatabaseError(
                        f"Backup integrity check failed: {result!r}"
                    )
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {
            "path": str(destination),
            "bytes": destination.stat().st_size,
            "schemaVersion": self.schema_version(),
            "verified": True,
        }

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

    def set_emergency_stop(self, active):
        self.set_preference(
            "automation_emergency_stop",
            "1" if active else "0",
        )

    def emergency_stop_active(self):
        return self.get_preference(
            "automation_emergency_stop",
            "0",
        ) == "1"

    def acquire_execution_lease(
        self,
        probe_id,
        fingerprint,
        owner,
        expires_at,
    ):
        """Acquire one unexpired execution lease per probe."""

        now = self._now()
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM execution_leases WHERE expires_at <= ?",
                (now,),
            )
            try:
                connection.execute(
                    """
                    INSERT INTO execution_leases (
                        probe_id, fingerprint, owner,
                        acquired_at, expires_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        probe_id,
                        fingerprint,
                        owner,
                        now,
                        expires_at,
                    ),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def release_execution_lease(self, probe_id, fingerprint):
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM execution_leases
                WHERE probe_id = ? AND fingerprint = ?
                """,
                (probe_id, fingerprint),
            )

    def save_operation(self, operation):
        payload = operation.to_dict()
        now = self._now()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO operations (
                    id, name, objective, state, probe_id,
                    current_step, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    objective = excluded.objective,
                    state = excluded.state,
                    probe_id = excluded.probe_id,
                    current_step = excluded.current_step,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    operation.id,
                    operation.name,
                    operation.objective,
                    operation.state.value,
                    operation.probe_id,
                    operation.current_step,
                    self._json(payload),
                    now,
                    now,
                ),
            )

    def operation_records(self, state=None):
        if state is None:
            return self._rows(
                "SELECT * FROM operations ORDER BY created_at, id",
                (),
            )
        return self._rows(
            """
            SELECT * FROM operations
            WHERE state = ? ORDER BY created_at, id
            """,
            (str(state),),
        )

    def delete_operation(self, operation_id):
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM operations WHERE id = ?",
                (str(operation_id),),
            )
            return cursor.rowcount > 0

    def assign_fleet_role(
        self,
        asset_type,
        asset_id,
        role,
        operation_id=None,
        metadata=None,
    ):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO fleet_roles (
                    asset_type, asset_id, role,
                    operation_id, metadata_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_type, asset_id) DO UPDATE SET
                    role = excluded.role,
                    operation_id = excluded.operation_id,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    asset_type,
                    str(asset_id),
                    role,
                    operation_id,
                    self._json(metadata or {}),
                    self._now(),
                ),
            )

    def fleet_roles(self, asset_type=None):
        if asset_type is None:
            return self._rows(
                "SELECT * FROM fleet_roles ORDER BY asset_type, asset_id",
                (),
            )
        return self._rows(
            """
            SELECT * FROM fleet_roles
            WHERE asset_type = ? ORDER BY asset_id
            """,
            (asset_type,),
        )

    def set_event_state(
        self, domain, external_id, *, acknowledged=False,
        priority="normal", linked_operation_id=None,
    ):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO event_state (
                    domain, external_id, acknowledged, priority,
                    linked_operation_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(domain, external_id) DO UPDATE SET
                    acknowledged = excluded.acknowledged,
                    priority = excluded.priority,
                    linked_operation_id = excluded.linked_operation_id,
                    updated_at = excluded.updated_at
                """,
                (
                    domain, str(external_id), int(acknowledged), priority,
                    linked_operation_id, self._now(),
                ),
            )

    def event_state(self, domain, external_id):
        rows = self._rows(
            "SELECT * FROM event_state WHERE domain = ? AND external_id = ?",
            (domain, str(external_id)),
        )
        return rows[0] if rows else None

    def save_archive_report(self, report_id, title, content, kind="operational"):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO archive_reports (id, title, kind, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title, kind = excluded.kind,
                    content = excluded.content
                """,
                (report_id, title, kind, content, self._now()),
            )

    def archive_reports(self):
        return self._rows(
            "SELECT * FROM archive_reports ORDER BY created_at DESC, id", ()
        )

    def galaxy_map(self, max_age_seconds=None):
        """Return cartography until a scan or fleet arrival changes it.

        A focused-probe refresh records another detailed snapshot of its current
        sector, but that does not materially change fleet-scale cartography.
        Explicit scans and visit-history synchronization invalidate this cache.
        """

        from src.intelligence.galaxy import GalaxyMapBuilder

        now = time.monotonic()
        if (
            self._galaxy_cache is not None
            and (
                max_age_seconds is None
                or (
                    max_age_seconds > 0
                    and now - self._galaxy_cache_built_at < max_age_seconds
                )
            )
        ):
            return self._galaxy_cache

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
                SELECT * FROM (
                    SELECT sector_observations.*,
                           ROW_NUMBER() OVER (
                               PARTITION BY sector_x, sector_y, sector_z
                               ORDER BY observed_at DESC, id DESC
                           ) AS observation_rank
                    FROM sector_observations
                )
                WHERE observation_rank = 1
                """
            ).fetchall()

        galaxy = GalaxyMapBuilder().build(
            fleet_history,
            probe_histories,
        )
        for row in observations:
            galaxy.record_observation(
                json.loads(row["payload_json"]),
                probe_id=row["probe_id"],
            )

        self._galaxy_cache = galaxy
        self._galaxy_cache_built_at = now
        return galaxy

    def _invalidate_galaxy_cache(self):
        self._galaxy_cache = None
        self._galaxy_cache_built_at = 0.0

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

                CREATE TABLE IF NOT EXISTS execution_leases (
                    probe_id INTEGER PRIMARY KEY,
                    fingerprint TEXT NOT NULL UNIQUE,
                    owner TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    state TEXT NOT NULL,
                    probe_id INTEGER,
                    current_step INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_operations_state
                ON operations(state, updated_at);

                CREATE TABLE IF NOT EXISTS fleet_roles (
                    asset_type TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    operation_id TEXT,
                    metadata_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(asset_type, asset_id),
                    FOREIGN KEY(operation_id) REFERENCES operations(id)
                );

                CREATE TABLE IF NOT EXISTS event_state (
                    domain TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    acknowledged INTEGER NOT NULL DEFAULT 0,
                    priority TEXT NOT NULL DEFAULT 'normal',
                    linked_operation_id TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY(domain, external_id),
                    FOREIGN KEY(linked_operation_id) REFERENCES operations(id)
                );

                CREATE TABLE IF NOT EXISTS archive_reports (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
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
