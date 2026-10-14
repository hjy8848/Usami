"""Single-patch evolution with deterministic gates and immutable rollback."""
from __future__ import annotations
import json

from ..models import Consumption, EpisodeEvidence
from ..reflection.reflector import ReflectionInput
from ..reflection.scope import DomainPolicy
from ..skills.library import apply_patch
from ..skills.validation import StaticSkillGate
from .gates import DynamicGate, consumption_sum
from .models import DomainCoverage, EvolutionRecord, GatePolicy


class Evolver:
    def __init__(self, role, adapter, reflector, library_store, archive, policy=None):
        self.role, self.adapter, self.reflector = role, adapter, reflector
        self.library_store, self.archive = library_store, archive
        self.policy = policy or GatePolicy()

    def update(self, generation, customer, service, evidence, discovery_cases, service_task_cases=(), episode_prefix=None):
        discovery_cases, service_task_cases = tuple(discovery_cases), tuple(service_task_cases)
        parent = customer if self.role == "customer" else service
        evidence = tuple(EpisodeEvidence.model_validate(row.model_dump(mode="json")) for row in evidence)
        if any(row.config.partition != "development" for row in evidence):
            raise ValueError("heldout evidence cannot influence evolution")
        for row in evidence:
            checked = self.adapter.replay(row, self.library_store.load(row.customer_snapshot_hash),
                                          self.library_store.load(row.service_snapshot_hash))
            if not checked.verified:
                raise ValueError("evolution evidence failed independent replay: " + checked.reason)
        cases = tuple(discovery_cases) + tuple(service_task_cases)
        if not discovery_cases:
            raise ValueError("evolution requires at least one Discovery validation case")
        if any(case.config.partition != "development" for case in cases):
            raise ValueError("heldout cases cannot influence evolution")
        prefix = episode_prefix or ("g" + str(generation) + "." + self.role + ".validation")
        preflight = []
        if self.role == "service":
            # The actual normal-task results are part of the one Reflection,
            # including legal completion and correct refusal, not only attacks.
            gate = DynamicGate(self.adapter, self.archive, self.policy)
            for case in service_task_cases:
                preflight.append(gate._case(case, customer, service, prefix + ".reflection-task." + case.id))
            evidence += tuple(preflight)
        tools = tuple(sorted({name for case in cases for name in self.adapter.public_capabilities(case.config)}))
        forbidden = tuple(sorted({name for case in cases for name in (
            self.adapter.forbidden_identifiers(case.config) if hasattr(self.adapter, "forbidden_identifiers") else ())}))
        policies = [self.adapter.public_policy(case.config) for case in cases if hasattr(self.adapter, "public_policy")]
        value = ReflectionInput(generation=generation, role=self.role, library=parent, evidence=evidence,
                                interaction_views=tuple(self.adapter.reflection_view(row) for row in evidence)
                                if hasattr(self.adapter, "reflection_view") else None,
                                domain_policy=DomainPolicy(add_domains=tuple(sorted({case.config.domain for case in cases}))),
                                allowed_tools=tools, public_policy=json.dumps(policies, ensure_ascii=False, sort_keys=True))
        reflection = self.reflector.reflect(value)
        costs = consumption_sum((Consumption(reflection_calls=reflection.calls), *(row.consumption for row in preflight)))
        fields = dict(generation=generation, role=self.role, parent_customer_hash=customer.snapshot_hash,
                      parent_service_hash=service.snapshot_hash, reflection=reflection, patch=reflection.patch,
                      selected_snapshot_hash=parent.snapshot_hash)
        if reflection.error or reflection.patch is None:
            return EvolutionRecord(**fields, outcome="rejected", reasons=(reflection.error or "missing_patch",), consumption=costs)
        declared = reflection.patch.skill.scope.domains if reflection.patch.skill is not None else ()
        fields["domain_coverage"] = DomainCoverage(declared_domains=declared, validated_domains=(), unvalidated_domains=declared)
        static = StaticSkillGate(allowed_tools=tools, forbidden_identifiers=forbidden,
                                 allowed_domains={case.config.domain for case in cases}).validate(parent, reflection.patch)
        fields["static_validation"] = static
        if not static.passed:
            return EvolutionRecord(**fields, outcome="rejected", reasons=static.reasons, consumption=costs)
        if reflection.patch.action == "NOOP":
            return EvolutionRecord(**fields, outcome="noop", reasons=("explicit_noop",), consumption=costs)
        try:
            candidate = apply_patch(parent, reflection.patch, source=prefix + ".reflection")
            self.library_store.save(candidate, publish=False)
            fields["candidate_snapshot_hash"] = candidate.snapshot_hash
            gate = DynamicGate(self.adapter, self.archive, self.policy)
            if self.role == "customer":
                result = gate.customer(parent, candidate, service, discovery_cases, prefix)
            else:
                result = gate.service(customer, parent, candidate, discovery_cases, service_task_cases, evidence, prefix)
            fields["dynamic_validation"] = result
            validated = result.validated_domains or ()
            fields["domain_coverage"] = DomainCoverage(declared_domains=declared, validated_domains=validated,
                                                     unvalidated_domains=tuple(domain for domain in declared if domain not in validated))
            costs = consumption_sum((costs, result.consumption))
            if not result.passed:
                return EvolutionRecord(**fields, outcome="rejected", reasons=result.reasons, consumption=costs)
            self.library_store.save(candidate)
        except (ValueError, TypeError, OSError) as exc:
            return EvolutionRecord(**fields, outcome="rejected", reasons=("candidate_validation_error: " + str(exc),), consumption=costs)
        fields["selected_snapshot_hash"] = candidate.snapshot_hash
        return EvolutionRecord(**fields, outcome="accepted", reasons=("development_gate_passed",), consumption=costs)


class CustomerEvolver(Evolver):
    def __init__(self, adapter, reflector, library_store, archive, policy=None):
        super().__init__("customer", adapter, reflector, library_store, archive, policy)


class ServiceEvolver(Evolver):
    def __init__(self, adapter, reflector, library_store, archive, policy=None):
        super().__init__("service", adapter, reflector, library_store, archive, policy)
