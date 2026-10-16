from typing import Literal, Optional, Tuple
from pydantic import Field
from vast_coevo.schema import FrozenModel, digest
from vast_coevo.skills.models import Hash

Branch = Literal['error_amplification', 'correct_to_failure']
Ablation = Literal['random_legal', 'error_only', 'correct_only', 'bidirectional', 'bidirectional_fixed_designer']
Status = Literal['construction_failed', 'valid_not_triggered', 'triggered_correct', 'verified_failure',
                 'reproduced_failure', 'candidate_new_root_cause', 'confirmed_new_root_cause', 'triggered_unresolved']


class SearchPolicy(FrozenModel):
    version: Literal['designer-paired-v1'] = 'designer-paired-v1'
    min_pairs: int = Field(default=8, ge=4, strict=True)
    min_sources: int = Field(default=4, ge=2, strict=True)
    bootstrap_samples: int = Field(default=2000, ge=100, strict=True)
    bootstrap_seed: int = 731
    confidence: float = Field(default=.95, gt=.5, lt=1)
    max_valid_rate_drop: float = Field(default=.05, ge=0, le=1)
    max_trigger_rate_drop: float = Field(default=.05, ge=0, le=1)
    max_duplicate_rate_increase: float = Field(default=.05, ge=0, le=1)
    require_token_usage: bool = True
    max_token_cost_ratio: float = Field(default=1.25, ge=1)
    max_call_cost_ratio: float = Field(default=1.25, ge=1)


class Discovery(FrozenModel):
    trial_id: str
    evidence_hash: Optional[Hash] = None
    scene_hash: Optional[Hash] = None
    status: Status
    expected_kind: Optional[Literal["completion", "policy_refusal"]] = None
    known_failure_test: bool = False
    business_operations: int = 0
    construction_valid: bool = False
    triggered: bool = False
    verified_failure: bool = False
    direct_failure: bool = False
    fingerprint: Optional[Hash] = None
    root_key: Optional[Hash] = None
    root_state: Literal['none', 'candidate', 'confirmed'] = 'none'
    root_reason: str = ''
    duplicate: bool = False
    service_hash: Hash
    replay_verified: bool = True
    correct_legal: bool = False
    correct_refusal: bool = False
    business_violations: int = 0
    direct_business_violations: int = 0
    incidental_business_violations: int = 0
    source_hash: Optional[Hash] = None


class Selection(FrozenModel):
    decision: Literal['ACCEPT', 'REJECT', 'INCONCLUSIVE']
    reasons: Tuple[str, ...]
    paired_interval: Optional[Tuple[float, float]] = None
    paired_effect: float = 0
    baseline: dict
    candidate: dict
    parent_hash: Hash
    candidate_hash: Hash
    selected_hash: Hash
