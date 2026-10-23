"""Small immutable JSON archive; hashes audit records, not machine ownership."""
from pathlib import Path
import json
import os
import re

from .protocol import canonical, digest


class Archive:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, value):
        ref = digest(value)
        path = self.root / (ref + ".json")
        text = canonical(value)
        if path.exists():
            if path.read_text() != text:
                raise ValueError("archived record was modified")
        else:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
        return ref

    def load(self, ref):
        if not re.fullmatch(r"[0-9a-f]{64}", ref):
            raise ValueError("invalid archive reference")
        value = json.loads((self.root / (ref + ".json")).read_text())
        if digest(value) != ref:
            raise ValueError("archive integrity mismatch")
        return value


def chain(events):
    previous, rows = "", []
    for index, event in enumerate(events):
        row = {"index": index, "previous": previous, "event": event}
        row["hash"] = digest(row)
        rows.append(row)
        previous = row["hash"]
    return rows


def verify_chain(rows):
    previous = ""
    for index, row in enumerate(rows):
        if (row["index"] != index or row["previous"] != previous
                or row["hash"] != digest({k: v for k, v in row.items() if k != "hash"})):
            raise ValueError("research event chain was modified")
        previous = row["hash"]
    return previous
