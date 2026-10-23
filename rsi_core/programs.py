"""Immutable program identities. Candidate code never executes in this module."""
import ast
from dataclasses import asdict, dataclass
import re

from .protocol import CandidateError, digest


@dataclass(frozen=True)
class ProgramArtifact:
    kind: str
    source: str
    parent_ref: str = ""
    protocol: str = "rsi-python-v0.1"

    def __post_init__(self):
        if self.kind not in {"P", "M"} or self.protocol != "rsi-python-v0.1":
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


class ProgramStore:
    def __init__(self, root):
        from pathlib import Path
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, program):
        from .protocol import canonical
        path = self.root / (program.ref + ".json")
        contents = canonical(asdict(program))
        if path.exists():
            if path.read_text() != contents:
                raise ValueError("immutable program artifact was modified")
        else:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(contents)
        return program.ref

    def load(self, ref):
        import json
        if not re.fullmatch(r"[0-9a-f]{64}", ref):
            raise ValueError("invalid program reference")
        program = ProgramArtifact(**json.loads((self.root / (ref + ".json")).read_text()))
        if program.ref != ref:
            raise ValueError("program artifact integrity mismatch")
        return program
