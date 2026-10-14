from __future__ import annotations
from typing import Literal, Optional, Tuple
from pydantic import Field, model_validator

from ..models import Consumption, EpisodeConfig, ModelSpec
from ..schema import FrozenModel
from ..skills.models import Hash, SkillPatch, SkillRole
from ..skills.validation import StaticValidation
from ..reflection.reflector import ReflectionRecord


class ValidationCase(FrozenModel):
    id: str = Field(min_length=1)
    config: EpisodeConfig
    task_ref: Optional[str] = None
    purpose: Optional[Literal["legal_completion", "correct_refusal"]] = None

    @model_validator(mode="after")
    def development_only(self):
        if self.config.partition != "development":
            raise ValueError("heldout cases cannot enter candidate validation")
        if self.purpose is not None and self.task_ref is None:
            raise ValueError("normal task purpose requires a task reference")
        return self


class GatePolicy(FrozenModel):
    customer_allow_equal: bool = True
    service_allow_equal_without_failure: bool = True
    require_known_failure_reproduction: bool = True
    require_legal_tasks: bool = True
    require_refusal_tasks: bool = True


class ValidationMetrics(FrozenModel):
    valid_actions: int = Field(default=0, ge=0, strict=True)
    invalid_attempts: int = Field(default=0, ge=0, strict=True)
    business_violations: int = Field(default=0, ge=0, strict=True)
    authorization_anomalies: int = Field(default=0, ge=0, strict=True)
    false_rejections: int = Field(default=0, ge=0, strict=True)
    execution_errors: int = Field(default=0, ge=0, strict=True)
    legal_task_successes: int = Field(default=0, ge=0, strict=True)
    correct_refusals: int = Field(default=0, ge=0, strict=True)
    fingerprints: Tuple[Hash, ...] = ()
    replay_verified: bool = True


class GateResult(FrozenModel):
    passed: bool
    reasons: Tuple[str, ...]
    baseline: ValidationMetrics
    candidate: ValidationMetrics
    baseline_evidence: Tuple[Hash, ...]
    candidate_evidence: Tuple[Hash, ...]
    repaired: Tuple[Hash, ...] = ()
    consumption: Consumption
    validated_domains: Optional[Tuple[str, ...]] = Field(default=None, exclude_if=lambda value: value is None)


class DomainCoverage(FrozenModel):
    """Coverage describes executions, never a model's claim of generalization."""
    declared_domains: Tuple[str, ...]
    validated_domains: Tuple[str, ...]
    unvalidated_domains: Tuple[str, ...]


class EvolutionRecord(FrozenModel):
    schema_version: Literal[1] = 1
    generation: int = Field(ge=0, strict=True)
    role: SkillRole
    parent_customer_hash: Hash
    parent_service_hash: Hash
    reflection: ReflectionRecord
    patch: Optional[SkillPatch] = None
    static_validation: Optional[StaticValidation] = None
    dynamic_validation: Optional[GateResult] = None
    candidate_snapshot_hash: Optional[Hash] = None
    selected_snapshot_hash: Hash
    outcome: Literal["accepted", "rejected", "noop"]
    reasons: Tuple[str, ...] = ()
    consumption: Consumption
    domain_coverage: Optional[DomainCoverage] = Field(default=None, exclude_if=lambda value: value is None)


class RunConfig(FrozenModel):
    schema_version: Literal[1] = 1
    run_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
    generations: int = Field(default=1, ge=1, strict=True)
    exploration_cases: Tuple[ValidationCase, ...] = Field(min_length=1)
    validation_cases: Tuple[ValidationCase, ...] = Field(min_length=1)
    service_task_cases: Tuple[ValidationCase, ...] = ()
    customer_reflector_model: ModelSpec
    service_reflector_model: ModelSpec
    max_llm_calls: int = Field(default=500, ge=2, strict=True)
    max_tool_calls: int = Field(default=1000, ge=0, strict=True)
    policy: GatePolicy = Field(default_factory=GatePolicy)
    initial_customer_hash: Hash
    initial_service_hash: Hash

    @model_validator(mode="after")
    def fixed_models(self):
        from ..models import ModelSpec
        object.__setattr__(self, "customer_reflector_model", ModelSpec.model_validate(self.customer_reflector_model))
        object.__setattr__(self, "service_reflector_model", ModelSpec.model_validate(self.service_reflector_model))
        if any(c.task_ref is not None for c in self.exploration_cases + self.validation_cases):
            raise ValueError("Discovery worlds cannot contain task references")
        if any(c.task_ref is None for c in self.service_task_cases):
            raise ValueError("Service regression cases require native task references")
        pairs = {(c.config.customer_model.model_dump_json(), c.config.service_model.model_dump_json()) for c in self.exploration_cases + self.validation_cases + self.service_task_cases}
        if len(pairs) != 1:
            raise ValueError("base Agent models must be frozen throughout a run")
        return self
