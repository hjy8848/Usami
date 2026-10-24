"""Immutable program and version identities. Candidate code never executes here."""
import ast
from dataclasses import asdict, dataclass
import json
import re

from .protocol import CandidateError, ModelSnapshot, digest


@dataclass(frozen=True)
class ProgramArtifact:
    kind: str
    source: str
    parent_ref: str = ""
    protocol: str = "rsi-python-v0.2"

    def __post_init__(self):
        if self.kind not in {"P", "M"} or self.protocol != "rsi-python-v0.2":
            raise ValueError("invalid program protocol/kind")
        if not isinstance(self.source, str) or not self.source.strip():
            raise CandidateError("program source is empty")
        if self.parent_ref and not re.fullmatch(r"[0-9a-f]{64}", self.parent_ref):
            raise ValueError("invalid parent reference")

    @property
    def entrypoint(self):
        return "step" if self.kind == "P" else "next_step"

    @property
    def ref(self):
        return digest(asdict(self))

    def check(self, max_bytes=65536):
        if len(self.source.encode("utf-8")) > max_bytes:
            raise CandidateError("program source budget exceeded")
        try:
            tree = ast.parse(self.source)
        except (SyntaxError, ValueError, RecursionError) as exc:
            raise CandidateError("program syntax invalid: " + str(exc)) from exc
        entries = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and n.name == self.entrypoint]
        if len(entries) != 1 or isinstance(entries[0], ast.AsyncFunctionDef):
            raise CandidateError("program needs exactly one synchronous " + self.entrypoint)
        args = entries[0].args
        if (len(args.posonlyargs) + len(args.args) != 2 or args.vararg or args.kwarg
                or args.kwonlyargs or args.defaults or entries[0].decorator_list):
            raise CandidateError("entrypoint must accept exactly (view, state)")
        # This is a contract check, not a sandbox. OS isolation is mandatory.
        return self


@dataclass(frozen=True)
class ExperienceArtifact:
    """Immutable Service experience K, stored as canonical JSON."""

    content_json: str = "{}"
    parent_ref: str = ""
    protocol: str = "rsi-experience-v0.2"

    def __post_init__(self):
        if self.protocol != "rsi-experience-v0.2":
            raise ValueError("invalid experience protocol")
        value = json.loads(self.content_json)
        if not isinstance(value, dict) or self.content_json != json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False):
            raise ValueError("experience must be a canonical JSON object")
        if self.parent_ref and not re.fullmatch(r"[0-9a-f]{64}", self.parent_ref):
            raise ValueError("invalid experience parent reference")

    @classmethod
    def from_value(cls, value, parent_ref=""):
        if not isinstance(value, dict):
            raise CandidateError("Service experience K must be an object")
        try:
            content = json.dumps(value, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise CandidateError("Service experience K must be finite canonical JSON") from exc
        return cls(content, parent_ref)

    @property
    def value(self):
        return json.loads(self.content_json)

    @property
    def ref(self):
        return digest(asdict(self))


@dataclass(frozen=True)
class ServiceSnapshot:
    """Atomic fixed-B plus complete (P, K) Service version."""

    business_model_ref: str
    policy: ProgramArtifact
    experience: ExperienceArtifact
    parent_ref: str = ""
    evaluation_only: bool = False
    protocol: str = "rsi-service-snapshot-v0.2"

    def __post_init__(self):
        if self.protocol != "rsi-service-snapshot-v0.2" or not self.business_model_ref:
            raise ValueError("invalid Service snapshot protocol or fixed business model")
        if self.policy.kind != "P":
            raise ValueError("Service snapshots require a P policy program")
        if not isinstance(self.experience, ExperienceArtifact):
            raise ValueError("Service snapshots require an immutable K artifact")
        if self.parent_ref and not re.fullmatch(r"[0-9a-f]{64}", self.parent_ref):
            raise ValueError("invalid Service snapshot parent reference")

    @property
    def kind(self):
        return "SERVICE_BUNDLE"

    @property
    def ref(self):
        return digest(asdict(self))

    @property
    def policy_ref(self):
        return self.policy.ref

    @property
    def experience_ref(self):
        return self.experience.ref

    def evaluation_copy(self):
        return ServiceSnapshot(self.business_model_ref, self.policy, self.experience,
                               self.parent_ref, True)


@dataclass(frozen=True)
class DesignerSnapshot:
    """Atomic (research-model φ, executable research program M) version."""

    research_model: ModelSnapshot
    research_program: ProgramArtifact
    parent_ref: str = ""
    protocol: str = "rsi-designer-snapshot-v0.2"

    def __post_init__(self):
        if self.protocol != "rsi-designer-snapshot-v0.2":
            raise ValueError("invalid Designer snapshot protocol")
        if self.research_program.kind != "M":
            raise ValueError("Designer snapshots require an M research program")
        if self.parent_ref and not re.fullmatch(r"[0-9a-f]{64}", self.parent_ref):
            raise ValueError("invalid Designer snapshot parent reference")

    @property
    def ref(self):
        return digest(asdict(self))


class ProgramStore:
    def __init__(self, root):
        from pathlib import Path
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, program):
        from .protocol import canonical
        if isinstance(program, ServiceSnapshot):
            self.save(program.policy)
            self.save(program.experience)
            data = {"artifact_type": "service_snapshot_v0.2", **asdict(program)}
        elif isinstance(program, DesignerSnapshot):
            self.save(program.research_program)
            data = {"artifact_type": "designer_snapshot_v0.2", **asdict(program)}
        elif isinstance(program, ExperienceArtifact):
            data = {"artifact_type": "experience_v0.2", **asdict(program)}
        elif isinstance(program, ProgramArtifact):
            data = asdict(program)
        else:
            raise TypeError("unsupported immutable artifact")
        path = self.root / (program.ref + ".json")
        contents = canonical(data)
        if path.exists():
            if path.read_text() != contents:
                raise ValueError("immutable program artifact was modified")
        else:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(contents)
        return program.ref

    def load(self, ref):
        if not re.fullmatch(r"[0-9a-f]{64}", ref):
            raise ValueError("invalid program reference")
        data = json.loads((self.root / (ref + ".json")).read_text())
        artifact_type = data.pop("artifact_type", "")
        if artifact_type == "experience_v0.2":
            program = ExperienceArtifact(**data)
        elif artifact_type == "service_snapshot_v0.2":
            data["policy"] = ProgramArtifact(**data["policy"])
            data["experience"] = ExperienceArtifact(**data["experience"])
            program = ServiceSnapshot(**data)
        elif artifact_type == "designer_snapshot_v0.2":
            data["research_model"] = ModelSnapshot(**data["research_model"])
            data["research_program"] = ProgramArtifact(**data["research_program"])
            program = DesignerSnapshot(**data)
        else:
            program = ProgramArtifact(**data)
        if program.ref != ref:
            raise ValueError("program artifact integrity mismatch")
        return program

    def publish_service(self, snapshot, *, parent_ref=""):
        if not isinstance(snapshot, ServiceSnapshot) or snapshot.evaluation_only:
            raise ValueError("evaluation-only or non-Service artifacts cannot enter the main chain")
        if snapshot.parent_ref != parent_ref:
            raise ValueError("Service snapshot parent differs from the selected main-chain version")
        if parent_ref:
            parent = self.load(parent_ref)
            if not isinstance(parent, ServiceSnapshot):
                raise ValueError("Service parent reference does not identify a Service snapshot")
            if parent.business_model_ref != snapshot.business_model_ref:
                raise ValueError("fixed Service business model changed across snapshots")
            if snapshot.policy.parent_ref != parent.policy.ref:
                raise ValueError("Service policy does not inherit the selected parent policy")
            if snapshot.experience.parent_ref != parent.experience.ref:
                raise ValueError("Service experience does not inherit the selected parent experience")
        elif snapshot.policy.parent_ref or snapshot.experience.parent_ref:
            raise ValueError("genesis Service policy and experience cannot inherit an unpublished parent")
        return self.save(snapshot)

    def publish_designer(self, snapshot, *, parent_ref=""):
        if not isinstance(snapshot, DesignerSnapshot) or snapshot.parent_ref != parent_ref:
            raise ValueError("Designer snapshot parent differs from the selected main-chain version")
        if parent_ref and not isinstance(self.load(parent_ref), DesignerSnapshot):
            raise ValueError("Designer parent reference does not identify a Designer snapshot")
        if parent_ref:
            parent = self.load(parent_ref)
            if (snapshot.research_model.model_id != parent.research_model.model_id
                    or snapshot.research_model.sampling != parent.research_model.sampling):
                raise ValueError("Designer update may change φ weights only; base model and sampling stay fixed")
            if (snapshot.research_program.ref != parent.research_program.ref
                    and snapshot.research_program.parent_ref != parent.research_program.ref):
                raise ValueError("Designer program does not inherit the selected parent M")
        elif snapshot.research_program.parent_ref:
            raise ValueError("genesis Designer program cannot inherit an unpublished parent M")
        return self.save(snapshot)
