"""Container-only entrypoint; receives only source, public view and explicit state."""
import contextlib
import io
import json
import resource
import sys


def main():
    request = json.load(sys.stdin)
    try:
        namespace = {"__name__": "candidate"}
        # User stdout is not our wire protocol. OS/container limits, rather
        # than this redirect, enforce the untrusted-code security boundary.
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(request["source"], "<candidate>", "exec"), namespace)
            output = namespace[request["entrypoint"]](request["view"], request["state"])
        wire = json.dumps({"ok": True, "output": output,
                           "cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime
                           + resource.getrusage(resource.RUSAGE_SELF).ru_stime}, allow_nan=False)
    except Exception as exc:
        wire = json.dumps({"ok": False, "error": type(exc).__name__ + ": " + str(exc)[:2000],
                           "cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime})
    sys.stdout.write(wire)


if __name__ == "__main__":
    main()
