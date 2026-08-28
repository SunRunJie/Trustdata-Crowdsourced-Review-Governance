"""Profile every prior-research data file without modifying source data.

Outputs are deterministic manifests used by the project audit. CSV files are
read in chunks so that the same script can handle much larger later imports.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "prior_research" / "data"
CATALOG_PATH = ROOT / "data" / "source_catalog.csv"
PROFILE_PATH = ROOT / "data" / "source_profile.json"
CHUNK_SIZE = 25_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def profile_csv(path: Path) -> dict[str, Any]:
    row_count = 0
    missing: dict[str, int] = {}
    columns: list[str] = []
    dtypes: dict[str, str] = {}
    duplicate_rows = 0
    seen_hashes: set[int] = set()
    encoding_used = "utf-8-sig"

    try:
        iterator = pd.read_csv(path, chunksize=CHUNK_SIZE, encoding=encoding_used)
        first = True
        for chunk in iterator:
            if first:
                columns = [str(column) for column in chunk.columns]
                dtypes = {str(column): str(dtype) for column, dtype in chunk.dtypes.items()}
                first = False
            row_count += int(len(chunk))
            for column, value in chunk.isna().sum().items():
                missing[str(column)] = missing.get(str(column), 0) + int(value)
            hashes = pd.util.hash_pandas_object(chunk, index=False).astype("uint64")
            for value in hashes.tolist():
                number = int(value)
                if number in seen_hashes:
                    duplicate_rows += 1
                else:
                    seen_hashes.add(number)
    except UnicodeDecodeError:
        encoding_used = "latin-1"
        row_count = 0
        missing = {}
        columns = []
        dtypes = {}
        duplicate_rows = 0
        seen_hashes = set()
        first = True
        for chunk in pd.read_csv(path, chunksize=CHUNK_SIZE, encoding=encoding_used):
            if first:
                columns = [str(column) for column in chunk.columns]
                dtypes = {str(column): str(dtype) for column, dtype in chunk.dtypes.items()}
                first = False
            row_count += int(len(chunk))
            for column, value in chunk.isna().sum().items():
                missing[str(column)] = missing.get(str(column), 0) + int(value)
            hashes = pd.util.hash_pandas_object(chunk, index=False).astype("uint64")
            for value in hashes.tolist():
                number = int(value)
                if number in seen_hashes:
                    duplicate_rows += 1
                else:
                    seen_hashes.add(number)

    return {
        "rows": row_count,
        "columns": columns,
        "dtypes_first_chunk": dtypes,
        "missing_counts": missing,
        "duplicate_rows_exact": duplicate_rows,
        "encoding": encoding_used,
    }


def evidence_class(relative: str) -> str:
    normalized = relative.replace("\\", "/").lower()
    if "/raw/" in f"/{normalized}" and "collection_events" in normalized:
        return "collection_audit"
    if "/raw/" in f"/{normalized}":
        return "legacy_synthetic"
    if "/external/" in f"/{normalized}":
        return "third_party_archive"
    return "documentation"


def main() -> int:
    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(f"Missing source data directory: {SOURCE_ROOT}")

    records: list[dict[str, Any]] = []
    detailed: dict[str, Any] = {}
    for path in sorted(item for item in SOURCE_ROOT.rglob("*") if item.is_file()):
        relative = path.relative_to(ROOT).as_posix()
        record: dict[str, Any] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "extension": path.suffix.lower(),
            "evidence_class": evidence_class(relative),
        }
        if path.suffix.lower() == ".csv":
            try:
                csv_profile = profile_csv(path)
                record.update(
                    {
                        "rows": csv_profile["rows"],
                        "columns": len(csv_profile["columns"]),
                        "duplicate_rows_exact": csv_profile["duplicate_rows_exact"],
                        "encoding": csv_profile["encoding"],
                        "status": "profiled",
                    }
                )
                detailed[relative] = csv_profile
            except Exception as exc:  # audit must expose unreadable inputs
                record.update({"status": "failed", "error": repr(exc)})
        else:
            record["status"] = "hashed"
        records.append(record)

    catalog = pd.DataFrame(records)
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    catalog.to_csv(CATALOG_PATH, index=False, encoding="utf-8-sig")

    payload = {
        "source_root": SOURCE_ROOT.relative_to(ROOT).as_posix(),
        "file_count": len(records),
        "csv_count": int((catalog["extension"] == ".csv").sum()),
        "total_bytes": int(catalog["bytes"].sum()),
        "profiles": detailed,
    }
    PROFILE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    failed = catalog.loc[catalog["status"] == "failed"]
    print(f"[OK] Catalog: {CATALOG_PATH}")
    print(f"[OK] Detailed profile: {PROFILE_PATH}")
    print(f"[INFO] Files={len(records)} CSV={payload['csv_count']} Bytes={payload['total_bytes']}")
    if not failed.empty:
        print(f"[FAIL] Unreadable CSV files={len(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

