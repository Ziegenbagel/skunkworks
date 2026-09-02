import os
import unittest
from unittest.mock import patch

import requests

from src.api.client import GameClient
from src.api.contract import (
    ApiCompatibilityError,
    ApiRateLimitError,
    MAXIMUM_API_VERSION,
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
            [FakeResponse({"apiVersion": 130})]
        )

        self.assertEqual(
            client.ensure_compatible_api(),
            130,
        )
        self.assertEqual(MAXIMUM_API_VERSION, 130)

    def test_rejects_older_api(self):
        client = self.client(
            [FakeResponse({"apiVersion": 102})]
        )

        with self.assertRaises(ApiCompatibilityError):
            client.ensure_compatible_api()

    def test_forward_tolerates_unreviewed_newer_api(self):
        client = self.client(
            [FakeResponse({"apiVersion": 126}), FakeResponse({"id": 7})]
        )

        self.assertEqual(client.ensure_compatible_api(), 126)
        self.assertEqual(client.get_player(), {"id": 7})
        self.assertEqual(len(client.session.calls), 2)

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

    def test_account_rate_budget_is_shared_and_protects_background_capacity(self):
        GameClient._shared_rate_limits.clear()
        first = self.client([
            FakeResponse(
                {"id": 1},
                headers={
                    "X-RateLimit-Limit": "60",
                    "X-RateLimit-Remaining": "18",
                    "X-RateLimit-Reset": "4102444800",
                },
            ),
        ])

        first.get_player()
        second = self.client([])

        self.assertFalse(second.background_budget_available())
        self.assertTrue(second.background_budget_available(estimated_cost=5, reserve=12))
        GameClient._shared_rate_limits.clear()

    def test_unknown_rate_budget_does_not_block_initial_background_telemetry(self):
        GameClient._shared_rate_limits.clear()
        client = self.client([])

        self.assertTrue(client.background_budget_available())

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
