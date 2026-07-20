"""
Utilities for formatting time values used
throughout Skunkworks.
"""


def format_duration(
    seconds,
):
    """
    Convert a duration in seconds into a
    compact, human-readable string.
    """

    seconds = int(seconds)

    days, seconds = divmod(
        seconds,
        86400,
    )

    hours, seconds = divmod(
        seconds,
        3600,
    )

    minutes, seconds = divmod(
        seconds,
        60,
    )

    if days > 0:

        return (
            f"{days}d "
            f"{hours}h"
        )

    if hours > 0:

        return (
            f"{hours}h "
            f"{minutes}m"
        )

    if minutes > 0:

        if seconds > 0:

            return (
                f"{minutes}m "
                f"{seconds}s"
            )

        return f"{minutes}m"

    return f"{seconds} sec"