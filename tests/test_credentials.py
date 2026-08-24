import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.data import DataEngine
from src.security import CredentialStore
from src.ui.controller import MissionControlController


class MemoryKeyring:
    def __init__(self):
        self.value = None
        self.read_count = 0

    def get_password(self, service, account):
        self.read_count += 1
        return self.value

    def set_password(self, service, account, value):
        self.value = value

    def delete_password(self, service, account):
        self.value = None


class MemoryCredentialStore(CredentialStore):
    def __init__(self):
        super().__init__()
        self.backend = MemoryKeyring()

    def _keyring(self):
        return self.backend


class CredentialTests(unittest.TestCase):
    def test_key_round_trips_through_vault_without_environment_file(self):
        store = MemoryCredentialStore()
        with patch.dict(os.environ, {}, clear=True):
            store.save("secret-api-key")
            self.assertEqual(store.get(), "secret-api-key")
            self.assertEqual(store.source(), "operating_system_vault")
            store.delete()
            self.assertIsNone(store.get())

    def test_repeated_status_queries_read_the_vault_only_once(self):
        store = MemoryCredentialStore()
        store.backend.value = "secret-api-key"

        self.assertEqual(store.get(), "secret-api-key")
        self.assertTrue(store.get())
        self.assertEqual(store.source(), "operating_system_vault")

        self.assertEqual(store.backend.read_count, 1)

    def test_first_launch_requires_completion_and_credential(self):
        with tempfile.TemporaryDirectory() as temporary:
            engine = DataEngine(Path(temporary) / "settings.sqlite3")
            credentials = MemoryCredentialStore()
            controller = MissionControlController(
                settings_engine=engine,
                credential_store=credentials,
            )

            self.assertTrue(controller.onboardingRequired)
            self.assertFalse(controller.credentialConfigured)

            controller.saveApiKey("secret-api-key")

            self.assertTrue(controller.credentialConfigured)
            self.assertNotIn("secret-api-key", controller.credentialMessage)


if __name__ == "__main__":
    unittest.main()
