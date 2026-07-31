"""Durable action-journal facade."""


class ActionJournal:
    def __init__(self, data_engine):
        self.data_engine = data_engine

    def record(self, command, status, blockers=()):
        return self.data_engine.record_action(
            command.fingerprint,
            command.to_dict(),
            status,
            blockers,
        )

    def was_successful(self, fingerprint):
        return self.data_engine.action_was_successful(
            fingerprint
        )

    def entries(self, probe_id=None):
        return self.data_engine.action_history(probe_id)
