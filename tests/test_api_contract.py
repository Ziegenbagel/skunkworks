import os
import unittest
from unittest.mock import patch

from src.api.client import GameClient
from src.api.contract import (
    ApiCompatibilityError,
    ApiRateLimitError,
)


class FakeResponse:
    def __init__(
        self,
        payload,
        status_code=200,
        headers=None,
    ):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


class GameClientContractTests(unittest.TestCase):
    def client(self, responses):
        with patch.dict(
            os.environ,
            {"VON_NEUMANN_API_KEY": "test-key"},
        ):
            return GameClient(FakeSession(responses))

    def test_accepts_current_api(self):
        client = self.client(
            [FakeResponse({"apiVersion": 106})]
        )

        self.assertEqual(
            client.ensure_compatible_api(),
            106,
        )

    def test_rejects_older_api(self):
        client = self.client(
            [FakeResponse({"apiVersion": 102})]
        )

        with self.assertRaises(ApiCompatibilityError):
            client.ensure_compatible_api()

    def test_rejects_unreviewed_newer_api(self):
        client = self.client(
            [FakeResponse({"apiVersion": 107})]
        )

        with self.assertRaises(ApiCompatibilityError):
            client.ensure_compatible_api()

    def test_exposes_rate_limit_delay(self):
        client = self.client(
            [
                FakeResponse(
                    {},
                    status_code=429,
                    headers={"Retry-After": "12"},
                )
            ]
        )

        with self.assertRaises(ApiRateLimitError) as error:
            client.get_player()

        self.assertEqual(
            error.exception.retry_after_seconds,
            12,
        )


if __name__ == "__main__":
    unittest.main()
