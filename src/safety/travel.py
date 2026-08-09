"""Mission 15–16 travel hazard intelligence and route comparison."""

from dataclasses import dataclass
from math import prod

from src.models.galaxy import SectorCoordinates


@dataclass(frozen=True)
class Hazard:
    code: str
    severity: str
    message: str
    acknowledgement_recommended: bool = False
    probability_percent: float | None = None


@dataclass(frozen=True)
class RouteOption:
    name: str
    hops: tuple[SectorCoordinates, ...]
    collision_risk_percent: float
    container_risk_percent: float
    expected_integrity_loss_percent: float
    maximum_integrity_loss_percent: float
    fuel_cost: float
    fuel_sufficient: bool
    scut_protected: bool
    score: float


@dataclass(frozen=True)
class RouteAssessment:
    origin: SectorCoordinates
    destination: SectorCoordinates
    recommended: RouteOption
    options: tuple[RouteOption, ...]
    hazards: tuple[Hazard, ...]
    current_integrity_percent: float
    expected_arrival_integrity_percent: float
    worst_case_arrival_integrity_percent: float
    additional_container_count: int
    container_break_threshold: int
    forgotten_manny_names: tuple[str, ...]
    destination_black_hole: bool | None
    known_black_hole_sectors: tuple[SectorCoordinates, ...]
    unknown_hazard_sectors: tuple[SectorCoordinates, ...]

    @property
    def acknowledgement_recommended(self):
        return any(
            hazard.acknowledgement_recommended
            for hazard in self.hazards
        )


class TravelSafetyService:
    """Explain known travel risks without overriding player choice."""

    DESTRUCTION_RISK = {
        3: 5.0,
        4: 12.0,
        5: 25.0,
    }

    def __init__(self, world, travel, policy):
        self.world = world
        self.travel = travel
        self.policy = policy

    def assess(
        self,
        destination,
        route_mode="recommended",
        maximum_segment_distance=1,
    ):
        origin = self.travel.current_sector()

        if origin is None:
            return None

        direct = self._route_option(
            "direct",
            origin,
            (destination,),
        )
        segmented_hops = self.travel.route_to(
            destination,
            maximum_hop_distance=maximum_segment_distance,
        ) or ()
        segmented = self._route_option(
            "segmented",
            origin,
            segmented_hops,
        )
        if (
            route_mode == "segmented"
            and self.scut_beacon_corridor(origin, destination)
        ):
            # Transit beacons at both endpoints make the direct SCUT jump the
            # safe exception to ordinary segmented travel.
            options = self._unique_options(direct, segmented)
            recommended = direct
        elif route_mode == "segmented":
            # Adjacent destinations make direct and segmented routes
            # identical. Put the required mode first so de-duplication keeps
            # its identity instead of dropping it and leaving no segmented
            # option to select.
            options = self._unique_options(segmented, direct)
            recommended = options[0]
        elif route_mode == "direct":
            options = self._unique_options(direct, segmented)
            recommended = direct
        else:
            options = self._unique_options(direct, segmented)
            recommended = min(options, key=lambda option: option.score)
        current_integrity = self._integrity()
        hazard_knowledge = tuple(
            (
                sector,
                self._destination_black_hole(sector),
            )
            for sector in recommended.hops
        )
        black_holes = tuple(
            sector
            for sector, present in hazard_knowledge
            if present is True
        )
        unknown_sectors = tuple(
            sector
            for sector, present in hazard_knowledge
            if present is None
        )
        black_hole = self._destination_black_hole(destination)
        forgotten = self._forgotten_mannies()
        hazards = self._hazards(
            recommended,
            current_integrity,
            black_holes,
            unknown_sectors,
            forgotten,
        )

        return RouteAssessment(
            origin=origin,
            destination=destination,
            recommended=recommended,
            options=options,
            hazards=hazards,
            current_integrity_percent=current_integrity,
            expected_arrival_integrity_percent=max(
                0,
                current_integrity
                - recommended.expected_integrity_loss_percent,
            ),
            worst_case_arrival_integrity_percent=max(
                0,
                current_integrity
                - recommended.maximum_integrity_loss_percent,
            ),
            additional_container_count=(
                self.additional_container_count()
            ),
            container_break_threshold=(
                self.container_break_threshold()
            ),
            forgotten_manny_names=forgotten,
            destination_black_hole=black_hole,
            known_black_hole_sectors=black_holes,
            unknown_hazard_sectors=unknown_sectors,
        )

    def collision_risk(self, distance, scut_protected=False):
        if scut_protected or distance <= 2:
            return 0.0

        return self.DESTRUCTION_RISK.get(distance, 40.0)

    def additional_container_count(self):
        return sum(
            1
            for container in self.world.probe[
                "inventory"
            ].get("containers", [])
            if container.get("kind") == "container"
        )

    def container_break_threshold(self):
        response = getattr(
            self.world,
            "hazard_context",
            {},
        ).get(
            "damageWarnings"
        ) or {}
        rule = response.get("rule") or {}

        if rule.get("startsAtAdditionalContainers"):
            return int(
                rule["startsAtAdditionalContainers"]
            )

        model = self.world.probe.get("model", "generic")
        reinforced = self._reinforced_couplings()

        if model == "deuterium_tanker":
            return 4 if reinforced else 2

        return 10 if reinforced else 5

    def container_break_risk(self):
        count = self.additional_container_count()
        threshold = self.container_break_threshold()
        return min(
            100.0,
            max(0.0, (count - threshold + 1) * 10.0),
        )

    def scut_corridor(self, origin, destination):
        return bool(
            self.scut_networks_covering(origin)
            & self.scut_networks_covering(destination)
        )

    def scut_beacon_corridor(self, origin, destination):
        """Return whether both endpoints are active beacons on one network."""

        context = getattr(self.world, "hazard_context", {})
        endpoint_networks = []
        for endpoint in (origin, destination):
            networks = set()
            for index, response in enumerate(context.get("scutNetworks", [])):
                network = response.get("network", {})
                network_id = network.get("id", network.get("name", index))
                for relay in network.get("relays", []):
                    relative = (relay.get("sector") or {}).get("relative")
                    if (
                        relative
                        and relay.get("status") == "on"
                        and relay.get("isTransitBeacon") is True
                        and SectorCoordinates.from_api(relative) == endpoint
                    ):
                        networks.add(str(network_id))
                        break
            endpoint_networks.append(networks)
        return bool(endpoint_networks[0] & endpoint_networks[1])

    def scut_networks_covering(self, sector):
        """Return the known active SCUT networks covering one sector."""
        covered_by = set()
        context = getattr(self.world, "hazard_context", {})

        for index, response in enumerate(context.get("scutNetworks", [])):
            network = response.get("network", {})
            network_id = network.get("id", network.get("name", index))
            for relay in network.get("relays", []):
                relative = (relay.get("sector") or {}).get("relative")
                if not relative or relay.get("status") != "on":
                    continue
                relay_sector = SectorCoordinates.from_api(relative)
                radius = int(relay.get("coverageRadiusSectors", 0) or 0)
                if relay_sector.distance_to(sector) <= radius:
                    covered_by.add(str(network_id))
                    break

        return frozenset(covered_by)

    def scut_route_covered(self, origin, hops):
        """Return True/False for known coverage, or None when not loaded.

        Every leg must remain within the same active SCUT network.  The
        tri-state result lets lightweight/offline callers that did not load
        hazard context avoid mistaking missing data for confirmed exposure.
        """
        context = getattr(self.world, "hazard_context", {})
        if "scutNetworks" not in context:
            return None

        current = origin
        for target in hops:
            if not self.scut_corridor(current, target):
                return False
            current = target
        return True

    def _route_option(self, name, origin, hops):
        if not hops:
            return RouteOption(
                name=name,
                hops=(),
                collision_risk_percent=0,
                container_risk_percent=0,
                expected_integrity_loss_percent=0,
                maximum_integrity_loss_percent=0,
                fuel_cost=0,
                fuel_sufficient=True,
                scut_protected=False,
                score=0,
            )

        legs = []
        current = origin
        all_scut = True

        for target in hops:
            distance = current.distance_to(target)
            protected = self.scut_corridor(current, target)
            all_scut = all_scut and protected
            legs.append(
                (
                    distance,
                    self.collision_risk(
                        distance,
                        protected,
                    ),
                )
            )
            current = target

        collision = self._combined_risk(
            risk for _, risk in legs
        )
        container = self._combined_risk(
            self.container_break_risk()
            for _ in legs
        )
        total_distance = sum(distance for distance, _ in legs)
        expected_integrity = round(total_distance * 1.5, 2)
        maximum_integrity = round(total_distance * 3.0, 2)
        fuel_cost = round(
            len(hops) * self.travel.fuel_cost(),
            4,
        )
        fuel_sufficient = (
            self.travel.fuel_available() >= fuel_cost
        )
        score = (
            collision * 10
            + container * 2
            + expected_integrity
            + len(hops) * 0.5
        )

        if not fuel_sufficient:
            score += 10000

        if (
            all_scut
            and self.policy.prefer_scut_corridors
        ):
            score -= 5

        return RouteOption(
            name=name,
            hops=tuple(hops),
            collision_risk_percent=round(collision, 2),
            container_risk_percent=round(container, 2),
            expected_integrity_loss_percent=expected_integrity,
            maximum_integrity_loss_percent=maximum_integrity,
            fuel_cost=fuel_cost,
            fuel_sufficient=fuel_sufficient,
            scut_protected=all_scut,
            score=round(score, 2),
        )

    def _hazards(
        self,
        option,
        current_integrity,
        black_holes,
        unknown_sectors,
        forgotten,
    ):
        hazards = []

        if (
            self.policy.warn_on_collision_risk
            and option.collision_risk_percent > 0
        ):
            hazards.append(
                Hazard(
                    code="probe_collision_risk",
                    severity="extreme",
                    probability_percent=(
                        option.collision_risk_percent
                    ),
                    acknowledgement_recommended=(
                        option.collision_risk_percent
                        > self.policy
                        .collision_acknowledgement_percent
                    ),
                    message=(
                        f"Probe destruction risk is "
                        f"{option.collision_risk_percent:.1f}%."
                    ),
                )
            )

        if (
            self.policy.warn_on_container_risk
            and option.container_risk_percent > 0
        ):
            hazards.append(
                Hazard(
                    code="container_detachment_risk",
                    severity="danger",
                    probability_percent=(
                        option.container_risk_percent
                    ),
                    acknowledgement_recommended=(
                        option.container_risk_percent
                        > self.policy
                        .container_acknowledgement_percent
                    ),
                    message=(
                        "Chance of at least one container "
                        f"detachment across this route is "
                        f"{option.container_risk_percent:.1f}%."
                    ),
                )
            )

        expected_arrival = (
            current_integrity
            - option.expected_integrity_loss_percent
        )
        worst_arrival = (
            current_integrity
            - option.maximum_integrity_loss_percent
        )

        if (
            self.policy.warn_on_integrity_risk
            and worst_arrival
            < self.policy.minimum_arrival_integrity_percent
        ):
            hazards.append(
                Hazard(
                    code="arrival_integrity_low",
                    severity="danger",
                    acknowledgement_recommended=True,
                    message=(
                        "Expected arrival integrity is "
                        f"{max(0, expected_arrival):.1f}%; "
                        "worst case is "
                        f"{max(0, worst_arrival):.1f}%."
                    ),
                )
            )

        if not option.fuel_sufficient:
            hazards.append(
                Hazard(
                    code="route_fuel_shortfall",
                    severity="danger",
                    acknowledgement_recommended=True,
                    message=(
                        f"Recommended route costs "
                        f"{option.fuel_cost:.1f} deuterium; "
                        f"{self.travel.fuel_available():.1f} "
                        "is available."
                    ),
                )
            )

        if self.policy.warn_on_black_holes:
            if black_holes:
                hazards.append(
                    Hazard(
                        code="black_hole_entrapment",
                        severity="extreme",
                        acknowledgement_recommended=True,
                        message=(
                            "Recommended route enters known "
                            "black-hole sector(s): "
                            + ", ".join(
                                self._coordinate_label(sector)
                                for sector in black_holes
                            )
                            + ". Terminal entrapment is timed "
                            "after arrival in each such sector."
                        ),
                    )
                )
            if (
                unknown_sectors
                and self.policy.warn_on_unknown_destination
            ):
                hazards.append(
                    Hazard(
                        code="destination_hazards_unknown",
                        severity="caution",
                        message=(
                            f"{len(unknown_sectors)} route "
                            "sector(s) lack detailed stored "
                            "observations; black-hole risk is unknown."
                        ),
                    )
                )

        if (
            forgotten
            and self.policy.warn_on_forgotten_mannies
        ):
            hazards.append(
                Hazard(
                    code="mannies_left_behind",
                    severity="danger",
                    acknowledgement_recommended=True,
                    message=(
                        f"{len(forgotten)} Manny unit(s) outside "
                        "the probe will be left behind: "
                        + ", ".join(forgotten)
                    ),
                )
            )

        return tuple(hazards)

    def _coordinate_label(self, sector):
        return f"{sector.x}:{sector.y}:{sector.z}"

    def _forgotten_mannies(self):
        return tuple(
            manny.get("name", str(manny.get("id", "unknown")))
            for manny in self.world.mannies.get("mannies", [])
            if manny.get("location", {}).get("type") == "sector"
        )

    def _destination_black_hole(self, destination):
        record = (
            self.world.galaxy.get(destination)
            if self.world.galaxy is not None
            else None
        )

        if record is None or record.observed is None:
            return None

        objects = record.observed.get("sector", {}).get(
            "objects",
            [],
        )
        return any(
            object_.get("type") == "black_hole"
            for object_ in objects
        )

    def _integrity(self):
        return float(
            self.world.probe.get("systems", {}).get(
                "integrityPercent",
                100,
            )
        )

    def _reinforced_couplings(self):
        response = getattr(
            self.world,
            "hazard_context",
            {},
        ).get(
            "improvements"
        ) or {}
        return any(
            improvement.get("id")
            == "reinforced_container_couplings"
            and improvement.get("done", False)
            for improvement in response.get("improvements", [])
        )

    def _combined_risk(self, risks):
        probabilities = [
            max(0, min(100, risk)) / 100
            for risk in risks
        ]

        if not probabilities:
            return 0.0

        return (1 - prod(1 - risk for risk in probabilities)) * 100

    def _unique_options(self, *options):
        unique = []
        seen = set()

        for option in options:
            key = option.hops
            if key in seen:
                continue
            seen.add(key)
            unique.append(option)

        return tuple(unique)
