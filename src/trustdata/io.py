"""Input adapters and canonical-schema validation."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


SUPPORTED_SUFFIXES = {".csv", ".json", ".jsonl", ".parquet"}


def read_table(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported input format {suffix!r}; expected {sorted(SUPPORTED_SUFFIXES)}")
    if suffix == ".csv":
        return pd.read_csv(source, encoding="utf-8-sig")
    if suffix == ".jsonl":
        return pd.read_json(source, lines=True)
    if suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "records" in payload:
            payload = payload["records"]
        return pd.DataFrame(payload)
    try:
        return pd.read_parquet(source)
    except ImportError as exc:
        raise RuntimeError(
            "Parquet support requires a verified pyarrow or fastparquet installation"
        ) from exc


def write_table(frame: pd.DataFrame, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    suffix = destination.suffix.lower()
    if suffix == ".csv":
        frame.to_csv(destination, index=False, encoding="utf-8-sig")
    elif suffix == ".jsonl":
        frame.to_json(destination, orient="records", lines=True, force_ascii=False)
    elif suffix == ".json":
        destination.write_text(
            json.dumps({"records": frame.to_dict(orient="records")}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    elif suffix == ".parquet":
        try:
            frame.to_parquet(destination, index=False)
        except ImportError as exc:
            raise RuntimeError(
                "Parquet support requires a verified pyarrow or fastparquet installation"
            ) from exc
    else:
        raise ValueError(f"Unsupported output format: {suffix}")
    return destination

