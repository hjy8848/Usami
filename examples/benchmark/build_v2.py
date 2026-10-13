"""Deterministically freeze public v0.2; use --private-seed-base for local test."""
import argparse
from pathlib import Path
from usami.benchmark.release_v2 import build_release, freeze_service, HELD_OUT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("benchmarks/v0.2.0"))
    parser.add_argument("--private-seed-base", type=int)
    args = parser.parse_args()
    if args.private_seed_base is not None:
        if "private" not in args.out.resolve().parts: raise ValueError("private test must be written under an ignored private/ directory")
        if 2100000 <= args.private_seed_base < 2200000: raise ValueError("public demo seed range is not private")
        manifest, rejected = freeze_service(HELD_OUT, 8, args.private_seed_base, split="test", visibility="private")
        manifest.save(args.out / "service-test-private.json")
        print(f"Private instances: {len(manifest.instances)}; rejected: {len(rejected)}")
    else:
        result = build_release(args.out)
        print({"sizes": result["split_sizes"], "structures": result["structural_diversity"]["unique"]})


if __name__ == "__main__": main()
