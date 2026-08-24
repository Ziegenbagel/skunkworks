"""Operating-system-backed API credential storage."""

import os
import platform
import subprocess
import threading


class CredentialStore:
    SERVICE = "Skunkworks Mission Control"
    ACCOUNT = "von-neumann-api-key"
    ENVIRONMENT_KEY = "VON_NEUMANN_API_KEY"
    _process_cache_lock = threading.Lock()
    _process_cache_loaded = False
    _process_cache_value = None
    _process_cache_source = "none"

    def __init__(self):
        # Test doubles and specialized stores keep an instance-local cache;
        # ordinary application stores share one read for the process so every
        # service worker does not reopen the operating-system vault.
        self._cache_loaded = False
        self._cache_value = None
        self._cache_source = "none"

    @staticmethod
    def _keyring():
        try:
            import keyring
        except ImportError as error:
            raise RuntimeError(
                "Secure credential support is unavailable. Install the project runtime dependencies."
            ) from error
        return keyring

    def get(self):
        value, _source = self._cached_credential()
        return value

    def source(self):
        _value, source = self._cached_credential()
        return source

    def _cached_credential(self):
        owner = CredentialStore if type(self) is CredentialStore else self
        lock = (
            CredentialStore._process_cache_lock
            if owner is CredentialStore
            else threading.Lock()
        )
        loaded_name = (
            "_process_cache_loaded" if owner is CredentialStore else "_cache_loaded"
        )
        value_name = (
            "_process_cache_value" if owner is CredentialStore else "_cache_value"
        )
        source_name = (
            "_process_cache_source" if owner is CredentialStore else "_cache_source"
        )
        with lock:
            if getattr(owner, loaded_name, False):
                return getattr(owner, value_name), getattr(owner, source_name)
            value, source = self._read_credential()
            setattr(owner, loaded_name, True)
            setattr(owner, value_name, value)
            setattr(owner, source_name, source)
            return value, source

    def _read_credential(self):
        try:
            stored = self._keyring().get_password(self.SERVICE, self.ACCOUNT)
        except Exception:
            stored = self._macos_get()
        if stored:
            return stored, "operating_system_vault"
        environment = os.getenv(self.ENVIRONMENT_KEY)
        return environment, "environment" if environment else "none"

    def _set_cached_credential(self, value, source):
        owner = CredentialStore if type(self) is CredentialStore else self
        prefix = "_process_cache_" if owner is CredentialStore else "_cache_"
        lock = (
            CredentialStore._process_cache_lock
            if owner is CredentialStore
            else threading.Lock()
        )
        with lock:
            setattr(owner, prefix + "loaded", True)
            setattr(owner, prefix + "value", value)
            setattr(owner, prefix + "source", source)

    def save(self, api_key):
        value = str(api_key).strip()
        if not value:
            raise ValueError("API key cannot be empty.")
        try:
            self._keyring().set_password(self.SERVICE, self.ACCOUNT, value)
        except Exception as error:
            if not self._macos_save(value):
                raise RuntimeError(
                    "The operating-system credential vault is unavailable."
                ) from error
        self._set_cached_credential(value, "operating_system_vault")

    def delete(self):
        try:
            keyring = self._keyring()
            keyring.delete_password(self.SERVICE, self.ACCOUNT)
        except Exception:
            self._macos_delete()
        environment = os.getenv(self.ENVIRONMENT_KEY)
        self._set_cached_credential(
            environment,
            "environment" if environment else "none",
        )

    def _macos_get(self):
        if platform.system() != "Darwin":
            return None
        result = subprocess.run(
            ["security", "find-generic-password", "-s", self.SERVICE, "-a", self.ACCOUNT, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

    def _macos_save(self, value):
        if platform.system() != "Darwin":
            return False
        result = subprocess.run(
            ["security", "add-generic-password", "-U", "-s", self.SERVICE, "-a", self.ACCOUNT, "-w", value],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    def _macos_delete(self):
        if platform.system() != "Darwin":
            return False
        result = subprocess.run(
            ["security", "delete-generic-password", "-s", self.SERVICE, "-a", self.ACCOUNT],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode in {0, 44}
