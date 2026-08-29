"""Verify every input and output digest in the latest TrustData run manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="outputs/runs/latest/run_manifest.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    failures: list[str] = []
    checked = 0
    for section in ("inputs", "outputs"):
        for relative, expected in manifest[section].items():
            path = root / relative
            if not path.is_file():
                failures.append(f"missing: {relative}")
                continue
            actual = sha256(path)
            checked += 1
            if actual != expected:
                failures.append(f"digest mismatch: {relative}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print(f"[OK] verified {checked} manifest digests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
