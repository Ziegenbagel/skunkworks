"""Operating-system-backed API credential storage."""

import os
import platform
import subprocess


class CredentialStore:
    SERVICE = "Skunkworks Mission Control"
    ACCOUNT = "von-neumann-api-key"
    ENVIRONMENT_KEY = "VON_NEUMANN_API_KEY"

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
        try:
            stored = self._keyring().get_password(self.SERVICE, self.ACCOUNT)
        except Exception:
            stored = self._macos_get()
        return stored or os.getenv(self.ENVIRONMENT_KEY)

    def source(self):
        try:
            if self._keyring().get_password(self.SERVICE, self.ACCOUNT):
                return "operating_system_vault"
        except Exception:
            if self._macos_get():
                return "operating_system_vault"
        return "environment" if os.getenv(self.ENVIRONMENT_KEY) else "none"

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

    def delete(self):
        try:
            keyring = self._keyring()
            keyring.delete_password(self.SERVICE, self.ACCOUNT)
        except Exception:
            self._macos_delete()

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
