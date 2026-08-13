import os
import unittest
from unittest.mock import patch

import requests

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
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class GameClientContractTests(unittest.TestCase):
    def client(self, responses):
        with patch.dict(
            os.environ,
            {"VON_NEUMANN_API_KEY": "test-key"},
        ):
            return GameClient(FakeSession(responses))

    def test_accepts_current_api(self):
        client = self.client(
            [FakeResponse({"apiVersion": 107})]
        )

        self.assertEqual(
            client.ensure_compatible_api(),
            107,
        )

    def test_rejects_older_api(self):
        client = self.client(
            [FakeResponse({"apiVersion": 102})]
        )

        with self.assertRaises(ApiCompatibilityError):
            client.ensure_compatible_api()

    def test_rejects_unreviewed_newer_api(self):
        client = self.client(
            [FakeResponse({"apiVersion": 108})]
        )

        with self.assertRaises(ApiCompatibilityError):
            client.ensure_compatible_api()

        with self.assertRaises(ApiCompatibilityError):
            client.get_player()
        self.assertEqual(len(client.session.calls), 1)

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

    def test_retries_transient_disconnects_for_read_requests(self):
        delays = []
        with patch.dict(os.environ, {"VON_NEUMANN_API_KEY": "test-key"}):
            client = GameClient(
                FakeSession(
                    [
                        requests.ConnectionError("disconnected"),
                        requests.exceptions.ChunkedEncodingError("truncated"),
                        FakeResponse({"id": 42}),
                    ]
                ),
                sleeper=delays.append,
            )

        self.assertEqual(client.get_player(), {"id": 42})
        self.assertEqual(len(client.session.calls), 3)
        self.assertEqual(delays, [0.25, 0.5])

    def test_does_not_retry_mutating_requests(self):
        with patch.dict(os.environ, {"VON_NEUMANN_API_KEY": "test-key"}):
            client = GameClient(
                FakeSession([requests.ConnectionError("disconnected")]),
                sleeper=lambda _delay: None,
            )

        with self.assertRaises(requests.ConnectionError):
            client.request("POST", "/api/order", json={})

        self.assertEqual(len(client.session.calls), 1)


if __name__ == "__main__":
    unittest.main()
