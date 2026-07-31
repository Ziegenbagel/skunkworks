"""Durable multi-step objectives executed by automation."""

import json
from dataclasses import dataclass, field, replace
from enum import StrEnum
from uuid import uuid4


class OperationState(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OperationStep:
    action: str
    target: str | None = None
    status: str = "pending"
    resume_conditions: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "action": self.action,
            "target": self.target,
            "status": self.status,
            "resumeConditions": list(self.resume_conditions),
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class Operation:
    name: str
    objective: str
    steps: tuple[OperationStep, ...]
    probe_id: int | None = None
    state: OperationState = OperationState.PLANNED
    current_step: int = 0
    completion_conditions: tuple[str, ...] = ()
    failure_conditions: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"op-{uuid4()}")

    @property
    def current(self):
        if self.current_step >= len(self.steps):
            return None
        return self.steps[self.current_step]

    def activate(self):
        return replace(self, state=OperationState.ACTIVE)

    def pause(self, reason):
        metadata = dict(self.metadata)
        metadata["pauseReason"] = reason
        return replace(
            self,
            state=OperationState.PAUSED,
            metadata=metadata,
        )

    def advance(self):
        next_step = self.current_step + 1
        state = (
            OperationState.COMPLETED
            if next_step >= len(self.steps)
            else OperationState.ACTIVE
        )
        return replace(self, current_step=next_step, state=state)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "objective": self.objective,
            "probeId": self.probe_id,
            "state": self.state.value,
            "currentStep": self.current_step,
            "steps": [step.to_dict() for step in self.steps],
            "completionConditions": list(self.completion_conditions),
            "failureConditions": list(self.failure_conditions),
            "metadata": self.metadata,
        }


class OperationStore:
    def __init__(self, data_engine):
        self.data_engine = data_engine

    def save(self, operation):
        self.data_engine.save_operation(operation)
        return operation

    def records(self, state=None):
        return self.data_engine.operation_records(state)

    def all(self, state=None):
        return tuple(
            OperationFactory.from_dict(json.loads(record["payload_json"]))
            for record in self.records(state)
        )


class OperationFactory:
    """Build the initial repeatable operation templates."""

    TEMPLATES = {
        "expand_mining": (
            "select_resource_source", "establish_storage",
            "assign_miners", "schedule_transport",
        ),
        "establish_depot": (
            "select_asteroid", "deploy_containers",
            "assign_miners", "verify_depot",
        ),
        "fuel_recovery": (
            "select_deuterium_source", "mine_deuterium",
            "rendezvous_tanker", "transfer_deuterium",
        ),
        "build_hub": (
            "reserve_materials", "manufacture_components",
            "assemble_probe", "commission_hub",
        ),
        "recover_stranded_probe": (
            "locate_probe", "dispatch_tanker",
            "rendezvous", "transfer_deuterium",
        ),
        "production_campaign": (
            "reserve_inputs", "assign_workers",
            "manufacture_batch", "verify_inventory",
        ),
    }

    @classmethod
    def create(cls, template, *, probe_id=None, metadata=None):
        try:
            actions = cls.TEMPLATES[template]
        except KeyError as error:
            raise ValueError(f"Unknown operation template: {template}") from error
        title = template.replace("_", " ").title()
        return Operation(
            name=title,
            objective=title,
            probe_id=probe_id,
            steps=tuple(OperationStep(action) for action in actions),
            completion_conditions=("all_steps_succeeded",),
            failure_conditions=("operator_cancelled",),
            metadata={"template": template, **(metadata or {})},
        )

    @staticmethod
    def from_dict(value):
        return Operation(
            id=value["id"],
            name=value["name"],
            objective=value["objective"],
            probe_id=value.get("probeId"),
            state=OperationState(value.get("state", "planned")),
            current_step=value.get("currentStep", 0),
            steps=tuple(
                OperationStep(
                    action=step["action"],
                    target=step.get("target"),
                    status=step.get("status", "pending"),
                    resume_conditions=tuple(step.get("resumeConditions", ())),
                    metadata=step.get("metadata", {}),
                )
                for step in value.get("steps", ())
            ),
            completion_conditions=tuple(value.get("completionConditions", ())),
            failure_conditions=tuple(value.get("failureConditions", ())),
            metadata=value.get("metadata", {}),
        )
