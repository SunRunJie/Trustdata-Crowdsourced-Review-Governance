from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from trustdata.pipeline import run_pipeline


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@pytest.fixture(scope="session")
def benchmark_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("full-benchmark") / "results"
    run_pipeline(
        ROOT,
        ROOT / "configs" / "trust.yaml",
        output_dir=output,
        processed_dir=ROOT / "data" / "processed",
        publish=False,
    )
    return output


def _primary_at(output: Path, level: float) -> pd.Series:
    metrics = pd.read_csv(output / "classification_metrics.csv")
    return metrics.loc[
        metrics["contamination"].eq(level)
        & metrics["method"].eq("multi_evidence_logistic")
    ].iloc[0]


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
