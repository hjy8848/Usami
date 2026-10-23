"""Real OS isolation with an existing pinned Docker image; never auto-pulls."""
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
import uuid

from .protocol import BudgetExceeded, CandidateError, InfrastructureError, canonical


class DockerWorker:
    def __init__(self, image, limits):
        if not re.fullmatch(r"(?:[A-Za-z0-9_./:-]+@)?sha256:[0-9a-f]{64}", image):
            raise ValueError("worker image must be pinned to a full SHA256 digest")
        self.image, self.limits = image, limits
        check = subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=10)
        if check.returncode:
            raise InfrastructureError("pinned worker image is unavailable; no image was pulled")

    def invoke(self, program, view, state, ledger, scope):
        program.check(self.limits.source_bytes)
        payload = canonical({"source": program.source, "entrypoint": program.entrypoint,
                             "view": view, "state": state}).encode("utf-8")
        if len(payload) > self.limits.response_bytes:
            raise CandidateError("worker input exceeds serialized message budget")
        ledger.check()
        name = "rsi-" + uuid.uuid4().hex
        command = ["docker", "run", "--rm", "--pull", "never", "--name", name,
                   "--network", "none", "--read-only", "--cap-drop", "ALL",
                   "--security-opt", "no-new-privileges", "--pids-limit", "32",
                   "--memory", str(self.limits.memory_bytes), "--memory-swap", str(self.limits.memory_bytes),
                   "--cpus", "1", "--ulimit", "cpu=" + str(self.limits.cpu_seconds),
                   "--ulimit", "nofile=32:32", "--user", "65534:65534",
                   "--mount", "type=bind,source=" + str(Path(__file__).with_name("worker.py").resolve())
                   + ",target=/rsi-worker.py,readonly", "--entrypoint", "python", "-i", self.image,
                   "-I", "-S", "-B", "/rsi-worker.py"]
        started = time.monotonic()
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = bytearray()
        try:
            os.set_blocking(proc.stdin.fileno(), False)
            os.set_blocking(proc.stdout.fileno(), False)
            pending = memoryview(payload)
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdin, selectors.EVENT_WRITE)
                selector.register(proc.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    if time.monotonic() - started > self.limits.wall_seconds:
                        raise CandidateError("worker wall-clock limit exceeded")
                    if time.monotonic() - started > ledger.remaining("cpu_seconds"):
                        raise BudgetExceeded("root CPU upper-bound budget exhausted")
                    ledger.check()
                    for key, _ in selector.select(timeout=0.05):
                        if key.fileobj is proc.stdin:
                            if pending:
                                try:
                                    written = os.write(proc.stdin.fileno(), pending[:65536])
                                except BrokenPipeError:
                                    pending = pending[:0]
                                else:
                                    pending = pending[written:]
                            if not pending:
                                selector.unregister(proc.stdin)
                                proc.stdin.close()
                        else:
                            chunk = os.read(proc.stdout.fileno(), 65536)
                            if chunk:
                                output.extend(chunk)
                                if len(output) > self.limits.response_bytes:
                                    raise CandidateError("worker output exceeds message budget")
                            else:
                                selector.unregister(proc.stdout)
                proc.wait(timeout=2)
        finally:
            if proc.poll() is None:
                subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=10)
                proc.kill()
                proc.wait(timeout=5)
            proc.stdout.close()
            if not proc.stdin.closed:
                proc.stdin.close()
            # A candidate can forge its own reported resource usage. Charge a
            # Host-measured upper bound for the container's fixed one-vCPU
            # allocation, including failed invocations. This is deliberately
            # not represented as measured CPU utilization.
            ledger.charge(scope, cpu_seconds=time.monotonic() - started)
        if proc.returncode == 125:
            raise InfrastructureError("Docker failed to start the pinned worker")
        if proc.returncode != 0:
            raise CandidateError("candidate worker exited with status " + str(proc.returncode))
        try:
            response = json.loads(output)
        except (ValueError, UnicodeDecodeError) as exc:
            raise CandidateError("candidate corrupted the worker response protocol") from exc
        if not isinstance(response, dict) or type(response.get("ok")) is not bool:
            raise CandidateError("candidate corrupted the worker result envelope")
        if not response["ok"]:
            raise CandidateError(response["error"])
        canonical(response["output"])
        return response["output"]
