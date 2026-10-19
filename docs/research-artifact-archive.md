# Research artifact archive and deduplication

The pre-cleanup repository state is preserved on the archive branch
`archive/pre-dedupe-2026-10-19` (commit `4e6de2196f94c6c70100ac28bffbc442c4bcaacc`).
This branch keeps the original regular files at every path, so any archived artifact
can be restored without reconstructing it from a summary.

The complete pre-cleanup source archive is available as a
[GitHub-generated ZIP](https://github.com/hjy8848/Usami/archive/refs/heads/archive/pre-dedupe-2026-10-19.zip).
This preserves a full source tree on GitHub; it is not a separate object-storage
bucket.

The machine-readable inventory is [`research-artifact-archive-v1.json`](research-artifact-archive-v1.json).
It records every exact-content duplicate group found in the baseline tree, SHA-256,
the canonical copy, and whether a duplicate path was converted to a relative
symlink. The symlinked paths still resolve to the original bytes and remain at
their original names for local tools and Replay. Only files at least 100 KB with
`.json`, `.gz`, or `.zip` extensions were deduplicated; source code, small
configuration, logs, and documentation were left untouched.

## Verify

From the repository root, run:

```sh
python3 tools/verify_research_artifact_archive.py
```

The verifier checks the archive ref, every recorded content hash, and every
relative symlink target. A zero exit status means all paths still resolve to the
pre-cleanup bytes.

## Restore an original regular file

Restore one path from the preserved ref:

```sh
git restore --source=archive/pre-dedupe-2026-10-19 --worktree -- path/to/artifact
```

The full path list is in the JSON inventory. The archive branch must be retained
when the cleanup branch is merged.

## Scope and limits

Across 38 duplicate paths, deduplication replaces 84,525,169 repeated payload
bytes with 2,219 bytes of symlink text, saving 84,522,950 bytes. Including the
new archive records and verifier, the committed tree shrinks from 563,947,165
bytes across 2,166 files to 479,613,379 bytes across 2,170 files: a net
reduction of 84,333,786 bytes. No experiment runs, manifests, certificates, or
replay inputs were deleted. Git history is unchanged; this cleanup does not
rewrite commits or shrink old Git objects. Historical repository storage
requires a separate, explicitly reviewed operation.

The reduced tree uses standard relative Git symlinks. GitHub's repository
contents API follows a symlink when its target is a normal file in the same
repository ([GitHub documentation](https://docs.github.com/en/rest/repos/contents#get-repository-content)).
On a checkout that does not materialize symlinks, restore the affected path from
the archive ref using the command above.
