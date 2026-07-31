"""Runtime context shared by UI, operations, planning, and automation."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProbeContext:
    """The explicitly selected target probe."""

    id: int
    name: str
    model: str
    status: str
    is_default: bool
    is_reachable: bool

    @classmethod
    def from_summary(cls, probe):
        return cls(
            id=probe["id"],
            name=probe["name"],
            model=probe.get("model", "generic"),
            status=probe["status"],
            is_default=probe.get("isDefault", False),
            is_reachable=probe.get("isReachable", True),
        )


@dataclass(frozen=True)
class ApplicationContext:
    """Bound capabilities and world state for one selected probe."""

    probe: ProbeContext
    capabilities: object
    world: object | None = None
