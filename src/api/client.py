import os

import requests
from dotenv import load_dotenv


class GameClient:
    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("VON_NEUMANN_API_KEY")

        if not self.api_key:
            raise ValueError("VON_NEUMANN_API_KEY not found in .env")

        self.base_url = os.getenv(
            "VON_NEUMANN_BASE_URL",
            "https://neumann-probe.net",
        )

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def get_player(self):
        response = requests.get(
            f"{self.base_url}/api/me",
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    def get_probes(self):
        """Return every probe owned by the authenticated player."""

        response = requests.get(
            f"{self.base_url}/api/probes",
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()
        return response.json()

    def get_sector(self, probe_id):
        """Return observable sector and onboard inventory for one probe."""

        response = requests.get(
            f"{self.base_url}/api/probe/{probe_id}/sector",
            headers=self.headers,
            timeout=30,
        )

        response.raise_for_status()
        return response.json()