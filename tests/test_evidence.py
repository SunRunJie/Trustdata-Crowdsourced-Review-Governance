from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "outputs" / "runs" / "latest"
EVIDENCE = ROOT / "competition" / "evidence"
RUNTIME_MANIFEST = EVIDENCE / "runtime" / "run_manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _primary_at(level: float) -> pd.Series:
    metrics = pd.read_csv(LATEST / "classification_metrics.csv")
    return metrics.loc[
        metrics["contamination"].eq(level)
        & metrics["method"].eq("multi_evidence_logistic")
    ].iloc[0]


def test_numbers_master_matches_primary_results() -> None:
    numbers = pd.read_csv(EVIDENCE / "NUMBERS_MASTER.csv").set_index("number_id")
    primary = _primary_at(0.30)
    assert float(numbers.loc["N021", "value"]) == pytest.approx(primary["f1"], abs=5e-7)
    assert float(numbers.loc["N022", "value"]) == pytest.approx(primary["auprc"], abs=5e-7)
    assert float(numbers.loc["N023", "value"]) == pytest.approx(primary["fpr"], abs=5e-7)


def test_dashboard_headline_matches_primary_results() -> None:
    dashboard = json.loads((ROOT / "app" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    primary = _primary_at(0.30)
    assert dashboard["headline"]["risk_detection_f1_at_30pct"] == pytest.approx(primary["f1"])
    assert dashboard["headline"]["risk_detection_auprc_at_30pct"] == pytest.approx(primary["auprc"])
    assert dashboard["headline"]["false_positive_rate_at_30pct"] == pytest.approx(primary["fpr"])


def test_split_sensitivity_has_declared_coverage() -> None:
    detail = pd.read_csv(LATEST / "split_sensitivity_metrics.csv")
    summary = pd.read_csv(LATEST / "split_sensitivity_summary.csv")
    assert detail["split_seed"].nunique() == 5
    assert sorted(detail["contamination"].unique().tolist()) == [0.01, 0.05, 0.10, 0.20, 0.30]
    assert summary["split_runs"].eq(5).all()


def test_manifest_output_digests() -> None:
    manifest = json.loads((LATEST / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_status"] == "success"
    for relative_path, expected in manifest["outputs"].items():
        assert _sha256(ROOT / relative_path) == expected


def test_evidence_runtime_manifest_matches_latest_run() -> None:
    assert _sha256(RUNTIME_MANIFEST) == _sha256(LATEST / "run_manifest.json")


def test_evidence_mirror_matches_latest_results() -> None:
    for source in LATEST.glob("*.csv"):
        mirror = EVIDENCE / "results" / source.name
        assert mirror.exists()
        if source.name == "audit_trail.csv":
            latest_columns = pd.read_csv(source, nrows=0).columns.tolist()
            mirror_columns = pd.read_csv(mirror, nrows=0).columns.tolist()
            assert latest_columns == mirror_columns
            assert {"event_time", "model_version", "decision_status"}.issubset(latest_columns)
            continue
        assert _sha256(source) == _sha256(mirror)
