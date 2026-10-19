#!/usr/bin/env python3
"""Verify preserved research artifact bytes and deduplicated path links."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "research-artifact-archive-v1.json"


def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ref = data["archive_ref"]
    expected_commit = data["baseline_commit"]
    actual_commit = subprocess.check_output(
        ["git", "rev-parse", f"{ref}^{{commit}}"], cwd=ROOT, text=True
    ).strip()
    if actual_commit != expected_commit:
        raise SystemExit(f"archive ref mismatch: expected {expected_commit}, got {actual_commit}")

    archived_oids = {}
    for item in subprocess.check_output(
        ["git", "ls-tree", "-r", "-z", ref], cwd=ROOT
    ).split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        _mode, kind, object_id = metadata.decode("ascii").split()
        if kind == "blob":
            archived_oids[raw_path.decode("utf-8")] = object_id

    verified = 0
    linked = 0
    saved = 0
    for group in data["duplicate_groups"]:
        canonical = ROOT / group["canonical"]
        if canonical.is_symlink():
            raise SystemExit(f"canonical path must remain a regular file: {group['canonical']}")
        expected_blob = group["git_blob_oid"]
        if archived_oids.get(group["canonical"]) != expected_blob:
            raise SystemExit(f"canonical path missing from archive ref: {group['canonical']}")
        archived_content = subprocess.check_output(
            ["git", "show", f"{ref}:{group['canonical']}"], cwd=ROOT
        )
        archived_digest = hashlib.sha256(archived_content).hexdigest()
        if len(archived_content) != group["size_bytes"] or archived_digest != group["sha256"]:
            raise SystemExit(f"archived source mismatch: {group['canonical']}")
        for record in group["copies"]:
            path = ROOT / record["path"]
            if archived_oids.get(record["path"]) != expected_blob:
                raise SystemExit(f"archived blob mismatch: {record['path']}")
            if not path.is_file():
                raise SystemExit(f"missing archive path: {record['path']}")
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if len(content) != group["size_bytes"] or digest != group["sha256"]:
                raise SystemExit(f"content mismatch: {record['path']}")

            if record["representation"] == "relative_symlink":
                if not path.is_symlink():
                    raise SystemExit(f"expected a symlink: {record['path']}")
                target = os.readlink(path)
                expected_target = os.path.relpath(canonical, path.parent)
                if target != expected_target or path.resolve() != canonical.resolve():
                    raise SystemExit(f"symlink target mismatch: {record['path']} -> {target}")
                linked += 1
                saved += group["size_bytes"] - len(os.fsencode(target))
            elif path.is_symlink():
                raise SystemExit(f"unexpected symlink at preserved regular path: {record['path']}")
            verified += 1

    expected = data["deduplication"]["symlinked_duplicate_paths"]
    if linked != expected:
        raise SystemExit(f"expected {expected} symlinked paths, verified {linked}")
    if saved != data["deduplication"]["net_payload_bytes_saved"]:
        raise SystemExit(
            f"payload savings mismatch: expected {data['deduplication']['net_payload_bytes_saved']}, got {saved}"
        )
    print(
        f"OK: {len(data['duplicate_groups'])} duplicate groups, {verified} paths verified, "
        f"{linked} symlinks, {saved:,} payload bytes saved"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(f"archive verification failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
