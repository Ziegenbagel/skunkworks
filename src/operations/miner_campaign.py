"""Explainable, opt-in decisions for a stationary Miner-role probe."""

from dataclasses import dataclass

from src.planner.task import Task
from src.operations.logistics import TankerLogisticsService


@dataclass(frozen=True)
class MinerCampaignDecision:
    tasks: tuple[Task, ...] = ()
    phase: str = "paused"
    summary: str = "Miner automation is paused."
    paused: bool = True
    managed_resources: tuple[str, ...] = ()
    reserve_transfer_manny: bool = False
    reserve_ordinary_mannies: int = 0
    campaign_state: dict | None = None


class MinerCampaignService:
    """Select bounded mining work with a full-tank Manny transfer reserve."""

    ORDINARY_RESOURCES = ("metals", "ice", "carbon_compounds")

    def __init__(self, operations):
        self.operations = operations

    def decide(self, settings, *, target_probe=None, maximum_mining_order_amount=0.55,
               accepted_container_fills=None):
        if not settings.get("miningEnabled", False):
            return MinerCampaignDecision()
        mode = str(settings.get("resourceMode") or "deuterium")
        selected = []
        if mode in {"deuterium", "all"}:
            selected.append("deuterium")
        if mode in {"resources", "all"}:
            enabled = settings.get("ordinaryResources", ())
            selected.extend(item for item in self.ORDINARY_RESOURCES if item in enabled)
        managed = tuple(dict.fromkeys(selected))
        idle = self.operations.mining.idle_mannies()
        ordinary_worker_limit = max(
            1, min(4, int(settings.get("maximumMiningMannies", 4) or 4))
        )
        fuel = self.operations.world.probe.get("fuel") or {}
        fuel_amount = float(fuel.get("deuterium", 0) or 0)
        fuel_maximum = float(fuel.get("maxDeuterium", 0) or 0)
        deuterium_full = (
            "deuterium" in managed and fuel_maximum > 0
            and fuel_amount + 0.00001 >= fuel_maximum
        )
        tasks = []
        ordinary_managed = tuple(
            resource for resource in managed if resource != "deuterium"
        )
        if ordinary_managed:
            ordinary = self._ordinary_container_campaign(
                settings, ordinary_managed, ordinary_worker_limit,
                accepted_container_fills=accepted_container_fills,
            )
            reserve_task = self._empty_container_reserve_task(settings)
            # In combined mode the container workflow and deuterium mining may
            # coexist, but ordinary-resource mining itself is exclusively
            # owned by the staged container campaign below.
        else:
            ordinary = None
            reserve_task = None
        if "deuterium" in managed:
            transfer = self._deuterium_transfer(settings, target_probe)
            if transfer is not None:
                tasks.append(transfer)
        active = self.operations.mining.active_commitments()
        for resource in managed:
            if resource != "deuterium":
                continue
            if resource == "deuterium":
                # Every idle Manny mines until the tank is full. Once full,
                # retain exactly one aboard for transfer and let the rest mine
                # into their own waiting cargo state.
                remaining_workers = max(0, len(idle) - (1 if deuterium_full else 0))
            else:
                remaining_workers = min(ordinary_worker_limit, len(idle) - len(tasks))
            if remaining_workers <= 0:
                continue
            target = self.operations.mining.best_target(resource)
            if target is None:
                continue
            need = self._mineable_need(
                resource, target, active, allow_waiting=deuterium_full,
            )
            while need > 0.00001 and remaining_workers > 0:
                order_limit = (
                    float(maximum_mining_order_amount) * 100.0
                    if resource == "deuterium" else 0.25
                )
                order = min(need, order_limit)
                tasks.append(Task(
                    action="Mine Resource", category="mining",
                    # Retain the changing uncovered campaign amount in command
                    # identity. A later completed trip may legitimately send
                    # the same Manny back to the same asteroid.
                    target=str(target["id"]), quantity=round(need, 3),
                    maximum_order_amount=(
                        float(maximum_mining_order_amount)
                        if resource == "deuterium" else 0.25
                    ), resource_type=resource,
                    priority=1, workflow_authorized=True,
                    idempotency_scope=f"miner:{resource}:{target['id']}",
                    reason=(
                        f"Miner campaign is extracting {resource.replace('_', ' ')}."
                        + (" The full tank reserves one Manny for transfer; this worker may wait with mined fuel until capacity opens."
                           if resource == "deuterium" and deuterium_full else "")
                    ),
                    metadata={"minerCampaign": True},
                ))
                need -= order
                remaining_workers -= 1
        if ordinary is not None:
            tasks.extend(ordinary.tasks)
        if reserve_task is not None:
            tasks.append(reserve_task)
        if tasks:
            transferring = any(task.action == "Transfer Deuterium" for task in tasks)
            ordinary_is_primary = ordinary is not None and (
                bool(ordinary.tasks) or all(
                    task.metadata.get("emptyContainerReserve") for task in tasks
                )
            )
            if ordinary_is_primary:
                summary = ordinary.summary
                if reserve_task is not None:
                    summary += " Empty-container reserve replenishment is also queued."
            elif transferring and len(tasks) == 1:
                summary = "Tank is full; prepared transfer to the selected receiver."
            else:
                summary = f"Prepared {len(tasks)} Miner campaign order(s)."
                if deuterium_full:
                    summary += " One Manny is reserved for the full-tank transfer."
            return MinerCampaignDecision(
                tasks=tuple(tasks),
                phase=(ordinary.phase if ordinary_is_primary
                       else "transferring_deuterium" if transferring and len(tasks) == 1
                       else "mining"),
                paused=False,
                summary=summary,
                managed_resources=managed,
                reserve_transfer_manny=deuterium_full,
                reserve_ordinary_mannies=(
                    ordinary.reserve_ordinary_mannies if ordinary is not None else 0
                ),
                campaign_state=(ordinary.campaign_state if ordinary is not None else None),
            )
        if ordinary is not None:
            return MinerCampaignDecision(
                phase=ordinary.phase, paused=False, summary=ordinary.summary,
                managed_resources=managed,
                reserve_transfer_manny=deuterium_full,
                reserve_ordinary_mannies=ordinary.reserve_ordinary_mannies,
                campaign_state=ordinary.campaign_state,
            )
        deuterium_wait = self._deuterium_wait_status(settings, target_probe)
        if "deuterium" in managed and deuterium_wait is not None:
            phase, summary = deuterium_wait
            return MinerCampaignDecision(
                phase=phase, paused=False, summary=summary,
                managed_resources=managed,
                reserve_transfer_manny=deuterium_full,
            )
        return MinerCampaignDecision(
            phase="waiting_for_resource", paused=False,
            summary="No selected resource is currently mineable in this sector.",
            managed_resources=managed,
        )

    def _ordinary_container_campaign(
        self, settings, resources, worker_limit, *, accepted_container_fills=None,
    ):
        accepted_container_fills = accepted_container_fills or {}
        saved = settings.get("ordinaryContainerCampaign") or {}
        if isinstance(saved, dict) and isinstance(saved.get("campaigns"), list):
            states = [dict(item) for item in saved["campaigns"] if isinstance(item, dict)]
        elif isinstance(saved, dict) and saved:
            # Migrate the original single-campaign shape without abandoning an
            # in-flight container when parallel campaign support is enabled.
            states = [dict(saved)]
        else:
            states = []

        crew_count = len(self.operations.mannies.all())
        campaign_limit = max(1, crew_count // worker_limit)
        states = states[:campaign_limit]
        decisions = []
        next_states = []
        allocated_idle = 0

        for index in range(campaign_limit):
            state = states[index] if index < len(states) else {}
            current_container_id = str(state.get("containerId") or "")
            reserved_container_ids = {
                str(item.get("containerId")) for item in (*states, *next_states)
                if item.get("containerId") not in {None, ""}
            }
            reserved_container_ids.discard(current_container_id)
            decision = self._ordinary_single_container_campaign(
                state, resources, worker_limit,
                excluded_container_ids=reserved_container_ids,
                available_idle_count=max(
                    0, len(self.operations.mining.idle_mannies()) - allocated_idle,
                ),
                accepted_container_fills=accepted_container_fills,
            )
            decisions.append(decision)
            allocated_idle += len(decision.tasks)
            if decision.campaign_state:
                next_states.append(dict(decision.campaign_state))

        tasks = tuple(task for decision in decisions for task in decision.tasks)
        active = [decision for decision in decisions if decision.campaign_state]
        if not active:
            return MinerCampaignDecision(
                phase=decisions[0].phase if decisions else "waiting_for_resource",
                paused=False,
                summary=decisions[0].summary if decisions else "No ordinary-resource campaign is ready.",
                reserve_ordinary_mannies=0,
                campaign_state={"campaigns": []} if campaign_limit > 1 else {},
            )
        if len(active) == 1:
            phase = active[0].phase
            summary = active[0].summary
        else:
            phase = "parallel_container_campaigns"
            summary = (
                f"Running {len(active)} parallel container campaigns with up to "
                f"{worker_limit} Mannys per container. "
                + " ".join(decision.summary for decision in active)
            )
        active_campaign_mannies = self._active_campaign_manny_count(next_states)
        reserve_ordinary_mannies = min(
            len(self.operations.mining.idle_mannies()),
            max(0, campaign_limit * worker_limit - active_campaign_mannies),
        )
        return MinerCampaignDecision(
            tasks=tasks, phase=phase, paused=False, summary=summary,
            reserve_ordinary_mannies=reserve_ordinary_mannies,
            campaign_state=(
                {"campaigns": next_states}
                if campaign_limit > 1 or len(next_states) > 1
                else next_states[0]
            ),
        )

    def _ordinary_single_container_campaign(
        self, state, resources, worker_limit, *, excluded_container_ids=(),
        available_idle_count=None, accepted_container_fills=None,
    ):
        state = dict(state or {})
        resource = str(state.get("resourceType") or "")
        target_id = str(state.get("asteroidId") or "")
        container_id = str(state.get("containerId") or "")
        phase = str(state.get("phase") or "")

        if resource not in resources or not target_id or not container_id:
            resource = resources[0]
            target = self.operations.mining.best_target(resource)
            if target is None:
                return MinerCampaignDecision(
                    phase="waiting_for_resource", paused=False,
                    summary=f"No {resource.replace('_', ' ')} deposit is mineable in this sector.",
                    campaign_state={},
                )
            container = self._empty_attached_container(excluded_container_ids)
            if container is None:
                return MinerCampaignDecision(
                    phase="waiting_for_empty_container", paused=False,
                    summary=("Ordinary-resource mining requires one empty attached "
                             "additional container before mining can begin."),
                    campaign_state={},
                )
            target_id = str(target["id"])
            container_id = str(container["id"])
            phase = "deploy_container"
            state = {
                "resourceType": resource,
                "asteroidId": target_id,
                "containerId": container_id,
                "phase": phase,
            }

        attached = self._attached_container(container_id)
        detached = self._detached_container(container_id)
        active_types = self._active_container_task_types(container_id)
        expected_sector = self._sector(self.operations.world.probe)

        # The detach endpoint can accept the requested inventory ID while the
        # resulting sector observation identifies a different container as
        # the object anchored to that asteroid. Reconcile to the authoritative
        # live anchored object before replaying deployment. This is deliberately
        # limited to the deploy phase, the exact campaign asteroid, and a
        # container that still has room for the campaign payload.
        if phase == "deploy_container" and detached is None:
            anchored = self._available_anchored_container(
                target_id, excluded_container_ids,
            )
            if anchored is not None:
                container_id = str(
                    anchored.get("containerId") or anchored.get("id")
                )
                state["containerId"] = container_id
                detached = anchored
                attached = self._attached_container(container_id)
                active_types = self._active_container_task_types(container_id)

        # A persisted campaign pointer can outlive the selected container when
        # the game removes, renumbers, or otherwise stops reporting that
        # object. Do not let that stale pointer strand other live empty
        # containers. An active Manny reference is the telemetry-lag guard:
        # while a command is still operating on the selected container, retain
        # the durable campaign identity until the resulting object is visible.
        if (attached is None and detached is None
                and not self._campaign_container_is_active(container_id)):
            target = self.operations.mining.best_target(resource)
            container = self._empty_attached_container(excluded_container_ids)
            if target is None:
                return MinerCampaignDecision(
                    phase="waiting_for_resource", paused=False,
                    summary=f"No {resource.replace('_', ' ')} deposit is mineable in this sector.",
                    campaign_state={},
                )
            if container is None:
                return MinerCampaignDecision(
                    phase="waiting_for_empty_container", paused=False,
                    summary=("The previous campaign container is no longer visible. "
                             "Waiting for an empty attached additional container."),
                    campaign_state={},
                )
            target_id = str(target["id"])
            container_id = str(container["id"])
            phase = "deploy_container"
            state = {
                "resourceType": resource,
                "asteroidId": target_id,
                "containerId": container_id,
                "phase": phase,
            }
            attached = container
            detached = None
            active_types = set()

        if phase == "deploy_container":
            if detached is not None and self._container_targets(detached, target_id):
                phase = "mine_container"
                state["phase"] = phase
            elif "detach" in active_types:
                return self._ordinary_wait(
                    state, phase, "Waiting for the mining container deployment to complete."
                )
            elif attached is not None:
                return MinerCampaignDecision(
                    tasks=(Task(
                        action="Deploy Miner Container", category="miner_logistics",
                        target=container_id, priority=1, workflow_authorized=True,
                        idempotency_scope=f"miner-container:{container_id}:deploy:{target_id}",
                        reason=(f"Deploy empty container {container_id} to asteroid "
                                f"{target_id} before assigning miners."),
                        metadata={
                            "minerCampaign": True, "mode": "hidden_on_asteroid",
                            "objectId": target_id, "expectedSector": expected_sector,
                        },
                    ),),
                    phase=phase, paused=False,
                    summary="Deploying an empty container to the selected asteroid.",
                    campaign_state=state,
                )
            else:
                return self._ordinary_wait(
                    state, phase, "Waiting for the selected mining container to become visible."
                )

        if phase == "mine_container":
            detached = self._detached_container(container_id)
            if detached is None:
                if attached is not None and self._container_used(attached) >= 0.999:
                    phase = "release_container"
                    state["phase"] = phase
                else:
                    return self._ordinary_wait(
                        state, phase, "Waiting for the deployed mining container telemetry."
                    )
            else:
                used = self._container_used(detached)
                live_container_id = str(detached.get("id") or container_id)
                active_count = self._active_mining_count(
                    container_id, live_container_id,
                )
                accepted_amount = max(
                    float((accepted_container_fills or {}).get(container_id, 0) or 0),
                    float((accepted_container_fills or {}).get(live_container_id, 0) or 0),
                )
                # Detached asteroid objects currently omit contents and
                # usedCapacity. Accepted target-container orders are therefore
                # the durable lower bound on committed fill. Without journal
                # evidence, retain the active-order estimate used by pure
                # domain tests and compatibility callers.
                committed = max(
                    used,
                    accepted_amount,
                    used + active_count * 0.25 if not accepted_container_fills else 0,
                )
                remaining = max(0.0, 1.0 - committed)
                if committed >= 0.999 and active_count == 0:
                    phase = "recover_container"
                    state["phase"] = phase
                else:
                    target = self.operations.mining.best_target(resource)
                    available = float((target or {}).get("available_amount", 0) or 0)
                    worker_slots = max(0, worker_limit - active_count)
                    idle_count = (
                        len(self.operations.mining.idle_mannies())
                        if available_idle_count is None else available_idle_count
                    )
                    count = min(worker_slots, idle_count,
                                int((min(remaining, available) + 0.249999) / 0.25))
                    if count <= 0:
                        if active_count:
                            return self._ordinary_wait(
                                state, phase,
                                (f"{active_count} of {worker_limit} configured Manny mining "
                                 f"order(s) are filling container {container_id}; waiting for "
                                 "another worker slot or remaining container capacity."),
                            )
                        return self._ordinary_wait(
                            state, phase, "Waiting for four idle Mannys or remaining resource capacity."
                        )
                    tasks = tuple(Task(
                        action="Mine Resource", category="mining", target=target_id,
                        quantity=0.25, maximum_order_amount=0.25,
                        resource_type=resource, priority=1, workflow_authorized=True,
                        idempotency_scope=(f"miner-container:{container_id}:fill:"
                                           f"{active_count + index}:{used:g}"),
                        reason=(f"Fill container {container_id} with 0.25 ECE of "
                                f"{resource.replace('_', ' ')}."),
                        metadata={
                            "minerCampaign": True,
                            "targetContainerId": live_container_id,
                        },
                    ) for index in range(count))
                    return MinerCampaignDecision(
                        tasks=tasks, phase=phase, paused=False,
                        summary=(f"Sending {count} additional Manny miner(s) to place "
                                 f"0.25 ECE each into container {container_id}; "
                                 f"{active_count} already active."),
                        campaign_state=state,
                    )

        if phase == "recover_container":
            detached = self._detached_container(container_id)
            if attached is not None:
                phase = "release_container"
                state["phase"] = phase
            elif "recover" in active_types:
                return self._ordinary_wait(
                    state, phase, "Waiting for the full mining container recovery to complete."
                )
            elif detached is not None:
                return MinerCampaignDecision(
                    tasks=(Task(
                        action="Recover Miner Container", category="miner_logistics",
                        target=str(detached.get("id") or container_id),
                        priority=1, workflow_authorized=True,
                        idempotency_scope=f"miner-container:{container_id}:recover",
                        reason=f"Recover full mining container {container_id} from its asteroid.",
                        metadata={
                            "minerCampaign": True, "source": "asteroid",
                            "expectedSector": expected_sector,
                        },
                    ),),
                    phase=phase, paused=False,
                    summary="Recovering the full mining container from the asteroid.",
                    campaign_state=state,
                )

        if phase == "release_container":
            detached = self._detached_container(container_id)
            if detached is not None and self._container_is_drifting(detached):
                return MinerCampaignDecision(
                    phase="container_ready_for_transport", paused=False,
                    summary=(f"Container {container_id} is full and drifting for Transport pickup."),
                    campaign_state={},
                )
            if "detach" in active_types:
                return self._ordinary_wait(
                    state, phase, "Waiting for the full container to be released for Transport pickup."
                )
            if attached is not None:
                return MinerCampaignDecision(
                    tasks=(Task(
                        action="Release Miner Container", category="miner_logistics",
                        target=container_id, priority=1, workflow_authorized=True,
                        idempotency_scope=f"miner-container:{container_id}:release",
                        reason=f"Detach full container {container_id} to drift for Transport pickup.",
                        metadata={
                            "minerCampaign": True, "mode": "drifting",
                            "expectedSector": expected_sector,
                        },
                    ),),
                    phase=phase, paused=False,
                    summary="Releasing the full container to drift for Transport pickup.",
                    campaign_state=state,
                )

        return self._ordinary_wait(state, phase, "Waiting for live container state to advance.")

    def _empty_container_reserve_task(self, settings):
        desired = max(1, min(
            20, int(settings.get("minimumEmptyContainers", 2) or 2),
        ))
        empty = sum(
            self._container_used(container) <= 0.00001
            for container in self.operations.containers.attached()
        )
        manufacturing = getattr(self.operations, "manufacturing", None)
        if manufacturing is None:
            return None
        recipe_id = next((candidate for candidate in (
            "additional_container", "storage_container",
        ) if manufacturing.recipes.get(candidate) is not None), None)
        if recipe_id is None:
            return None
        active = manufacturing.active_production_count(recipe_id)
        shortage = max(0, desired - empty - active)
        if shortage <= 0:
            return None
        return Task(
            action="Craft Item", category="miner_logistics",
            target=recipe_id, quantity=shortage, priority=1,
            workflow_authorized=True,
            idempotency_scope=(
                f"miner-empty-container-reserve:{recipe_id}:{empty}:{active}:{desired}"
            ),
            reason=(f"Maintain {desired} empty attached container(s) for the "
                    f"ordinary-resource Miner campaign; {empty} are ready and "
                    f"{active} are currently being crafted."),
            metadata={
                "minerCampaign": True,
                "emptyContainerReserve": True,
                "desiredEmptyContainers": desired,
            },
        )

    @staticmethod
    def _ordinary_wait(state, phase, summary):
        return MinerCampaignDecision(
            phase=phase, paused=False, summary=summary, campaign_state=state,
        )

    def _empty_attached_container(self, excluded_container_ids=()):
        excluded = {str(value) for value in excluded_container_ids}
        return next((item for item in self.operations.containers.attached()
                     if self._container_used(item) <= 0.00001
                     and str(item.get("id", item.get("containerId"))) not in excluded), None)

    def _attached_container(self, container_id):
        return next((item for item in self.operations.containers.attached()
                     if str(item.get("id", item.get("containerId"))) == container_id), None)

    def _detached_container(self, container_id):
        return next((item for item in self.operations.containers.detached()
                     if container_id in {
                         str(item.get("id", "")),
                         str(item.get("containerId", "")),
                         str(item.get("sourceContainerId", "")),
                     }), None)

    def _available_anchored_container(self, target_id, excluded_container_ids=()):
        excluded = {str(value) for value in excluded_container_ids}
        candidates = (
            item for item in self.operations.containers.detached()
            if self._container_targets(item, target_id)
            and not self._container_is_drifting(item)
            and self.operations.containers.free_capacity(item) > 0.00001
            and not ({
                str(item.get("id", "")), str(item.get("containerId", "")),
            } & excluded)
        )
        return min(candidates, key=lambda item: str(item.get("id", "")), default=None)

    @staticmethod
    def _container_used(container):
        explicit = container.get("usedCapacity", container.get("used"))
        if explicit is not None:
            return float(explicit or 0)
        contents = container.get("contents") or container.get("resources") or {}
        if isinstance(contents, dict):
            return sum(float(value or 0) for value in contents.values())
        if isinstance(contents, (list, tuple)):
            return sum(float(
                item.get("amount", item.get("quantity", 0)) or 0
            ) for item in contents if isinstance(item, dict))
        return 0.0

    @staticmethod
    def _container_targets(container, target_id):
        target = (container.get("targetObjectId") or container.get("asteroidId")
                  or (container.get("location") or {}).get("objectId"))
        return str(target or "") == str(target_id)

    @staticmethod
    def _container_is_drifting(container):
        mode = str(container.get("mode") or container.get("state") or "").casefold()
        return mode in {"drifting", "detached"}

    def _active_container_task_types(self, container_id):
        types = set()
        for manny in self.operations.mannies.all():
            task = self._manny_task_payload(manny)
            text = str(self.operations.mannies._task_type(manny) or "").casefold()
            referenced = task.get("containerId") or task.get("targetContainerId")
            if referenced in {None, ""} or str(referenced) == container_id:
                if "detach" in text:
                    types.add("detach")
                if "recover" in text:
                    types.add("recover")
        return types

    def _campaign_container_is_active(self, container_id):
        for manny in self.operations.mannies.all():
            task = self._manny_task_payload(manny)
            references = (
                task.get("containerId"),
                task.get("targetContainerId"),
                task.get("objectId"),
            )
            if any(str(reference) == container_id for reference in references
                   if reference not in {None, ""}):
                return True
        return False

    def _active_mining_count(self, *container_ids):
        expected = {str(value) for value in container_ids if value not in {None, ""}}
        count = 0
        for manny in self.operations.mannies.all():
            task = self._manny_task_payload(manny)
            task_type = str(self.operations.mannies._task_type(manny) or "").casefold()
            if ("min" in task_type
                    and str(task.get("targetContainerId") or "") in expected):
                count += 1
        return count

    def _active_campaign_manny_count(self, states):
        expected = set()
        for state in states:
            container_id = str(state.get("containerId") or "")
            if not container_id:
                continue
            expected.add(container_id)
            detached = self._detached_container(container_id)
            if detached is not None:
                expected.add(str(detached.get("id") or ""))
        count = 0
        for manny in self.operations.mannies.all():
            task = self._manny_task_payload(manny)
            references = {
                str(task.get(key) or "")
                for key in ("containerId", "targetContainerId", "objectId")
            }
            if references & expected:
                count += 1
        return count

    @staticmethod
    def _manny_task_payload(manny):
        candidates = []
        for value in (manny.get("currentTask"), manny.get("task")):
            if isinstance(value, dict):
                candidates.append(value)
                for key in ("payload", "details", "parameters"):
                    if isinstance(value.get(key), dict):
                        candidates.append(value[key])
        merged = {}
        for candidate in candidates:
            merged.update(candidate)
        return merged

    def _deuterium_wait_status(self, settings, target_probe):
        fuel = self.operations.world.probe.get("fuel") or {}
        amount = float(fuel.get("deuterium", 0) or 0)
        maximum = float(fuel.get("maxDeuterium", 0) or 0)
        if maximum <= 0 or amount + 0.00001 < maximum:
            return None
        target_id = settings.get("deuteriumTransportProbeId")
        if target_id in {None, "", -1, "-1"} or target_probe is None:
            return ("tank_full_awaiting_receiver",
                    f"Deuterium tank is full at {amount:g}/{maximum:g} ECE. Select an available receiver.")
        if self._sector(self.operations.world.probe) != self._sector(target_probe):
            return ("tank_full_awaiting_rendezvous",
                    f"Deuterium tank is full at {amount:g}/{maximum:g} ECE. Waiting for the selected receiver to rendezvous in this sector.")
        target_fuel = target_probe.get("fuel") or {}
        target_amount = float(target_fuel.get("deuterium", 0) or 0)
        target_maximum = float(target_fuel.get("maxDeuterium", 0) or 0)
        if target_maximum <= target_amount + 0.00001:
            return ("tank_full_receiver_full",
                    f"Deuterium tank is full at {amount:g}/{maximum:g} ECE, but the selected receiver has no free fuel capacity.")
        return None

    def _deuterium_transfer(self, settings, target_probe):
        target_id = settings.get("deuteriumTransportProbeId")
        if target_id in {None, "", -1, "-1"} or target_probe is None:
            return None
        source = self.operations.world.probe
        source_fuel = source.get("fuel") or {}
        amount = float(source_fuel.get("deuterium", 0) or 0)
        maximum = float(source_fuel.get("maxDeuterium", 0) or 0)
        if maximum <= 0 or amount + 0.00001 < maximum:
            return None
        target_fuel = target_probe.get("fuel") or {}
        target_free = max(0.0, float(target_fuel.get("maxDeuterium", 0) or 0)
                          - float(target_fuel.get("deuterium", 0) or 0))
        plan = TankerLogisticsService().plan_delivery(
            source, target_probe, target_free, 1.0,
        )
        if plan.blockers:
            return None
        return Task(
            action="Transfer Deuterium", category="miner_logistics",
            target=str(plan.target_probe_id),
            quantity=round(plan.deliverable_amount, 2), priority=1,
            workflow_authorized=True,
            idempotency_scope=f"miner-transfer:{target_id}:{amount:g}",
            reason=("Miner tank is full; transfer mined Deuterium to the selected "
                    "same-sector Transport probe before resuming extraction."),
            metadata={"minerCampaign": True},
        )

    @staticmethod
    def _sector(probe):
        sector = probe.get("sector") or {}
        return sector.get("relative") or sector.get("relativeCoordinates")

    def _mineable_need(self, resource, target, active, *, allow_waiting=False):
        available = max(0.0, float(target.get("available_amount", 0) or 0))
        committed = max(0.0, float(active.get(resource, 0) or 0))
        if resource == "deuterium":
            if allow_waiting:
                return max(0.0, available - committed)
            fuel = self.operations.world.probe.get("fuel") or {}
            free = max(0.0, float(fuel.get("maxDeuterium", 0) or 0)
                       - float(fuel.get("deuterium", 0) or 0))
        else:
            free = max(0.0, float(self.operations.inventory.mining_return_capacity(active)))
        return max(0.0, min(available, free) - committed)
