"""Compatibility boundary for the Von Neumann Game API."""

MINIMUM_API_VERSION = 103
MAXIMUM_API_VERSION = 116


def api_is_compatible(version):
    """Forward-tolerate newer contracts; older ones may lack requirements."""

    return int(version) >= MINIMUM_API_VERSION


def api_is_reviewed(version):
    return MINIMUM_API_VERSION <= int(version) <= MAXIMUM_API_VERSION


class ApiCompatibilityError(RuntimeError):
    """Raised when the game API is older than Skunkworks requires."""


class ApiRateLimitError(RuntimeError):
    """Raised when the game API asks the client to delay further work."""

    def __init__(self, retry_after_seconds):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            "Von Neumann Game API rate limit reached; "
            f"retry after {retry_after_seconds} seconds."
        )
