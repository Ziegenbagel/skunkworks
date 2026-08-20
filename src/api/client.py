import os
import time

import requests
from dotenv import load_dotenv
from src.security import CredentialStore

from src.api.contract import (
    ApiCompatibilityError,
    ApiRateLimitError,
    MAXIMUM_API_VERSION,
    MINIMUM_API_VERSION,
    api_is_compatible,
)


class GameClient:
    """HTTP boundary for the Von Neumann Game API."""

    def __init__(
        self,
        session=None,
        api_key=None,
        credential_store=None,
        retry_attempts=2,
        retry_backoff_seconds=0.25,
        sleeper=None,
    ):
        load_dotenv()

        self.api_key = api_key or (credential_store or CredentialStore()).get()

        if not self.api_key:
            raise ValueError("Von Neumann API key is not configured. Open Settings or complete first-launch setup.")

        self.base_url = os.getenv(
            "VON_NEUMANN_BASE_URL",
            "https://neumann-probe.net",
        ).rstrip("/")
        self.session = session or requests.Session()
        self.retry_attempts = max(0, int(retry_attempts))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self._sleep = sleeper or time.sleep
        self.rate_limit = {}
        self.api_version = None

    def ensure_compatible_api(self):
        """Verify that the server satisfies the required API contract."""

        version = self.get_api_version()
        self.api_version = version

        if not api_is_compatible(version):
            raise ApiCompatibilityError(
                "Skunkworks requires Von Neumann Game API "
                f"v{MINIMUM_API_VERSION} or newer; server is v{version}. "
                f"The newest reviewed contract is v{MAXIMUM_API_VERSION}."
            )

        return version

    def get_api_version(self):
        response = self.request(
            "GET",
            "/api/version",
            authenticated=False,
        )
        return int(response["apiVersion"])

    def get_player(self):
        return self.request("GET", "/api/me")

    def get_probes(self):
        """Return every probe owned by the authenticated player."""

        return self.request("GET", "/api/probes")

    def get_probe(self, probe_id):
        """Return detailed information for one probe."""

        return self.request(
            "GET",
            f"/api/probe/{probe_id}",
        )

    def get_sector(self, probe_id):
        """Return observable sector and onboard inventory for one probe."""

        return self.request(
            "GET",
            f"/api/probe/{probe_id}/sector",
        )

    def get_mannies(self, probe_id):
        """Return authoritative Manny task state for one probe."""

        return self.request(
            "GET",
            f"/api/probe/{probe_id}/mannies",
        )

    def get_crafting_recipes(self):
        """Return all available crafting recipes."""

        return self.request(
            "GET",
            "/api/crafting-recipes",
        )

    def request(
        self,
        method,
        path,
        authenticated=True,
        **kwargs,
    ):
        if authenticated and self.api_version is not None and not api_is_compatible(
            self.api_version
        ):
            raise ApiCompatibilityError(
                "Live API commands are paused because Von Neumann Game API "
                f"v{self.api_version} predates Skunkworks' required contract "
                f"v{MINIMUM_API_VERSION}."
            )
        headers = {"Accept": "application/json"}

        if authenticated:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        method = method.upper()
        retryable = method in {"GET", "HEAD", "OPTIONS"}
        transient_errors = (
            requests.ConnectionError,
            requests.Timeout,
            requests.exceptions.ChunkedEncodingError,
        )

        for attempt in range(self.retry_attempts + 1):
            try:
                response = self.session.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=headers,
                    timeout=30,
                    **kwargs,
                )
                break
            except transient_errors:
                if not retryable or attempt >= self.retry_attempts:
                    raise
                self._sleep(
                    self.retry_backoff_seconds * (2 ** attempt)
                )
        self._capture_rate_limit(response)

        if response.status_code == 429:
            retry_after = int(
                response.headers.get("Retry-After", "60")
            )
            raise ApiRateLimitError(retry_after)

        response.raise_for_status()
        if response.status_code == 204:
            return {}
        return response.json()

    def _capture_rate_limit(self, response):
        mapping = {
            "limit": "X-RateLimit-Limit",
            "remaining": "X-RateLimit-Remaining",
            "reset": "X-RateLimit-Reset",
        }
        self.rate_limit = {
            key: response.headers[header]
            for key, header in mapping.items()
            if header in response.headers
        }
