from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from scripts.prepare_observed_data import prepare_observed_data
from trustdata.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "competition" / "evidence"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@pytest.fixture(scope="session")
def benchmark_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the full deterministic benchmark under pytest's ignored tmp tree."""
    workspace = tmp_path_factory.mktemp("full-benchmark")
    processed = workspace / "processed"
    output = workspace / "results"
    prepare_observed_data(processed)
    run_pipeline(
        ROOT,
        ROOT / "configs" / "trust.yaml",
        output_dir=output,
        processed_dir=processed,
        publish=False,
    )
    return output


def _primary_at(output: Path, level: float) -> pd.Series:
    metrics = pd.read_csv(output / "classification_metrics.csv")
    return metrics.loc[
        metrics["contamination"].eq(level)
        & metrics["method"].eq("multi_evidence_logistic")
    ].iloc[0]


def test_numbers_master_matches_generated_primary_results(benchmark_run: Path) -> None:
    numbers = pd.read_csv(EVIDENCE / "NUMBERS_MASTER.csv").set_index("number_id")
    primary = _primary_at(benchmark_run, 0.30)
    assert float(numbers.loc["N021", "value"]) == pytest.approx(primary["f1"], abs=5e-7)
    assert float(numbers.loc["N022", "value"]) == pytest.approx(primary["auprc"], abs=5e-7)
    assert float(numbers.loc["N023", "value"]) == pytest.approx(primary["fpr"], abs=5e-7)


def test_dashboard_headline_matches_generated_primary_results(benchmark_run: Path) -> None:
    dashboard = json.loads((ROOT / "app" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    primary = _primary_at(benchmark_run, 0.30)
    assert dashboard["headline"]["risk_detection_f1_at_30pct"] == pytest.approx(primary["f1"])
    assert dashboard["headline"]["risk_detection_auprc_at_30pct"] == pytest.approx(primary["auprc"])
    assert dashboard["headline"]["false_positive_rate_at_30pct"] == pytest.approx(primary["fpr"])


def test_split_sensitivity_has_declared_coverage(benchmark_run: Path) -> None:
    detail = pd.read_csv(benchmark_run / "split_sensitivity_metrics.csv")
    summary = pd.read_csv(benchmark_run / "split_sensitivity_summary.csv")
    assert detail["split_seed"].nunique() == 5
    assert sorted(detail["contamination"].unique().tolist()) == [0.01, 0.05, 0.10, 0.20, 0.30]
    assert summary["split_runs"].eq(5).all()


def test_generated_manifest_output_digests(benchmark_run: Path) -> None:
    manifest = json.loads((benchmark_run / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_status"] == "success"
    for relative_path, expected in manifest["outputs"].items():
        assert _sha256(ROOT / relative_path) == expected


def test_manifest_cli_verifies_generated_run(benchmark_run: Path) -> None:
    manifest = benchmark_run / "run_manifest.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_run_manifest.py"), "--manifest", str(manifest)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_versioned_evidence_mirrors_generated_results(benchmark_run: Path) -> None:
    for source in benchmark_run.glob("*.csv"):
        mirror = EVIDENCE / "results" / source.name
        assert mirror.exists()
        if source.name == "audit_trail.csv":
            generated = pd.read_csv(source)
            archived = pd.read_csv(mirror)
            assert generated.columns.tolist() == archived.columns.tolist()
            assert {"event_time", "model_version", "decision_status"}.issubset(generated.columns)
            assert generated.drop(columns=["event_time"]).equals(archived.drop(columns=["event_time"]))
            continue
        assert _sha256(source) == _sha256(mirror)
    for name in ("result_summary.json", "trust_passports.json"):
        assert _sha256(benchmark_run / name) == _sha256(EVIDENCE / "results" / name)
    for figure in (benchmark_run / "figures").glob("*.png"):
        archived_figure = EVIDENCE / "figures" / figure.name
        assert archived_figure.is_file()
        assert archived_figure.stat().st_size > 0


def test_versioned_runtime_manifest_declares_current_benchmark_contract() -> None:
    manifest = json.loads((EVIDENCE / "runtime" / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_status"] == "success"
    assert manifest["code_version"] == "0.2.0"
    assert manifest["random_seed"] == 20260828
    assert "outputs\\runs\\latest\\classification_metrics.csv" in manifest["outputs"]
