import os

import requests
from dotenv import load_dotenv

from src.api.contract import (
    ApiCompatibilityError,
    ApiRateLimitError,
    MAXIMUM_API_VERSION,
    MINIMUM_API_VERSION,
)


class GameClient:
    """HTTP boundary for the Von Neumann Game API."""

    def __init__(self, session=None):
        load_dotenv()

        self.api_key = os.getenv("VON_NEUMANN_API_KEY")

        if not self.api_key:
            raise ValueError("VON_NEUMANN_API_KEY not found in .env")

        self.base_url = os.getenv(
            "VON_NEUMANN_BASE_URL",
            "https://neumann-probe.net",
        ).rstrip("/")
        self.session = session or requests.Session()
        self.rate_limit = {}

    def ensure_compatible_api(self):
        """Verify that the server satisfies the required API contract."""

        version = self.get_api_version()

        if not (
            MINIMUM_API_VERSION
            <= version
            <= MAXIMUM_API_VERSION
        ):
            raise ApiCompatibilityError(
                "Skunkworks supports Von Neumann Game API "
                f"v{MINIMUM_API_VERSION} through "
                f"v{MAXIMUM_API_VERSION}; server is v{version}."
            )

        return version

    def get_api_version(self):
        response = self._request(
            "GET",
            "/api/version",
            authenticated=False,
        )
        return int(response["apiVersion"])

    def get_player(self):
        return self._request("GET", "/api/me")

    def get_probes(self):
        """Return every probe owned by the authenticated player."""

        return self._request("GET", "/api/probes")

    def get_probe(self, probe_id):
        """Return detailed information for one probe."""

        return self._request(
            "GET",
            f"/api/probe/{probe_id}",
        )

    def get_sector(self, probe_id):
        """Return observable sector and onboard inventory for one probe."""

        return self._request(
            "GET",
            f"/api/probe/{probe_id}/sector",
        )

    def get_mannies(self, probe_id):
        """Return authoritative Manny task state for one probe."""

        return self._request(
            "GET",
            f"/api/probe/{probe_id}/mannies",
        )

    def get_crafting_recipes(self):
        """Return all available crafting recipes."""

        return self._request(
            "GET",
            "/api/crafting-recipes",
        )

    def _request(
        self,
        method,
        path,
        authenticated=True,
        **kwargs,
    ):
        headers = {"Accept": "application/json"}

        if authenticated:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            timeout=30,
            **kwargs,
        )
        self._capture_rate_limit(response)

        if response.status_code == 429:
            retry_after = int(
                response.headers.get("Retry-After", "60")
            )
            raise ApiRateLimitError(retry_after)

        response.raise_for_status()
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
