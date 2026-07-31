"""Best-effort synchronization of live API state into the Data Engine."""

import sqlite3

import requests


class HistorySynchronizer:
    """Coordinate history reads without coupling DataEngine to HTTP."""

    def __init__(self, engine, capabilities):
        self.engine = engine
        self.capabilities = capabilities

    def sync(self, world, probe_id, reachable=True):
        failures = {}
        self.engine.record_world(world)

        self._attempt(
            failures,
            "fleet_visits",
            lambda: self.engine.sync_visits(
                self.capabilities.galaxy.visited_sectors()
            ),
        )

        if reachable:
            self._attempt(
                failures,
                "probe_visits",
                lambda: self.engine.sync_visits(
                    self.capabilities.probes.visited_sectors(
                        probe_id
                    ),
                    probe_id=probe_id,
                ),
            )
            self._record_response(
                failures,
                "messages",
                lambda: self.capabilities.messaging.received(
                    probe_id
                ),
                "messages",
                probe_id,
            )
            self._record_response(
                failures,
                "logbook_pages",
                lambda: self.capabilities.probes.logbook_pages(probe_id),
                "pages",
                probe_id,
            )
            self._record_response(
                failures,
                "alerts",
                lambda: self.capabilities.probes.alerts(
                    probe_id
                ),
                "alerts",
                probe_id,
            )
            self._record_response(
                failures,
                "damage_warnings",
                lambda: self.capabilities.probes.damage_warnings(
                    probe_id
                ),
                "warnings",
                probe_id,
            )

        self._record_response(
            failures,
            "sent_messages",
            self.capabilities.messaging.sent,
            "messages",
            None,
        )

        self._record_response(
            failures,
            "missions",
            self.capabilities.missions.list,
            "missions",
            None,
        )
        return failures

    def _record_response(
        self,
        failures,
        domain,
        load,
        collection_key,
        probe_id,
    ):
        def action():
            response = load()
            self.engine.record_records(
                domain,
                response.get(collection_key, []),
                probe_id=probe_id,
            )

        self._attempt(failures, domain, action)

    def _attempt(self, failures, name, action):
        try:
            action()
        except (
            OSError,
            RuntimeError,
            sqlite3.Error,
            requests.RequestException,
        ) as error:
            failures[name] = str(error)
