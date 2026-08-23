"""Player-configurable travel warning preferences."""

import json
from dataclasses import dataclass
from pathlib import Path

from src.application.paths import application_paths


PRESETS = {
    "cautious": {
        "collisionAcknowledgementPercent": 0,
        "containerAcknowledgementPercent": 0,
        "minimumArrivalIntegrityPercent": 50,
    },
    "balanced": {
        "collisionAcknowledgementPercent": 5,
        "containerAcknowledgementPercent": 10,
        "minimumArrivalIntegrityPercent": 30,
    },
    "bold": {
        "collisionAcknowledgementPercent": 25,
        "containerAcknowledgementPercent": 30,
        "minimumArrivalIntegrityPercent": 10,
    },
    "custom": {},
}


@dataclass(frozen=True)
class TravelSafetyPolicy:
    profile: str = "cautious"
    allow_risky_travel: bool = True
    warn_on_collision_risk: bool = True
    warn_on_container_risk: bool = True
    warn_on_integrity_risk: bool = True
    warn_on_black_holes: bool = True
    warn_on_forgotten_mannies: bool = True
    warn_on_unknown_destination: bool = True
    prefer_scut_corridors: bool = True
    collision_acknowledgement_percent: float = 0
    container_acknowledgement_percent: float = 0
    minimum_arrival_integrity_percent: float = 50

    def __post_init__(self):
        if self.profile not in PRESETS:
            raise ValueError(
                f"Unknown travel safety profile: {self.profile}"
            )

        for value in (
            self.collision_acknowledgement_percent,
            self.container_acknowledgement_percent,
            self.minimum_arrival_integrity_percent,
        ):
            if not 0 <= value <= 100:
                raise ValueError(
                    "Travel safety percentages must be 0–100."
                )

    @classmethod
    def from_dict(cls, value):
        profile = value.get("profile", "cautious")

        if profile not in PRESETS:
            raise ValueError(
                f"Unknown travel safety profile: {profile}"
            )

        merged = {
            **PRESETS[profile],
            **value,
        }
        return cls(
            profile=profile,
            allow_risky_travel=bool(
                merged.get("allowRiskyTravel", True)
            ),
            warn_on_collision_risk=bool(
                merged.get("warnOnCollisionRisk", True)
            ),
            warn_on_container_risk=bool(
                merged.get("warnOnContainerRisk", True)
            ),
            warn_on_integrity_risk=bool(
                merged.get("warnOnIntegrityRisk", True)
            ),
            warn_on_black_holes=bool(
                merged.get("warnOnBlackHoles", True)
            ),
            warn_on_forgotten_mannies=bool(
                merged.get("warnOnForgottenMannies", True)
            ),
            warn_on_unknown_destination=bool(
                merged.get("warnOnUnknownDestination", True)
            ),
            prefer_scut_corridors=bool(
                merged.get("preferScutCorridors", True)
            ),
            collision_acknowledgement_percent=float(
                merged.get(
                    "collisionAcknowledgementPercent",
                    0,
                )
            ),
            container_acknowledgement_percent=float(
                merged.get(
                    "containerAcknowledgementPercent",
                    0,
                )
            ),
            minimum_arrival_integrity_percent=float(
                merged.get(
                    "minimumArrivalIntegrityPercent",
                    50,
                )
            ),
        )


class TravelSafetyPolicyStore:
    def __init__(
        self,
        path=None,
    ):
        self.path = Path(path) if path is not None else application_paths().config_file(
            "travel_safety.json"
        )

    def load(self):
        if not self.path.exists():
            return TravelSafetyPolicy()

        with self.path.open("r", encoding="utf-8") as file:
            return TravelSafetyPolicy.from_dict(json.load(file))
