from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "outputs" / "runs" / "latest"

REQUIRED_FILES = (
    ROOT / "deliverables" / "TrustData_2026新域新质创新大赛申报书.docx",
    ROOT / "deliverables" / "TrustData_2026新域新质创新大赛申报书.pdf",
    ROOT / "deliverables" / "TrustData_2026新域新质创新大赛路演稿.pptx",
    ROOT / "product" / "index.html",
    ROOT / "product" / "dashboard-data.js",
    ROOT / "app" / "data" / "dashboard.json",
    ROOT / "scripts" / "assess_data.py",
    ROOT / "scripts" / "serve_solution.py",
    ROOT / "examples" / "sample_reviews.csv",
    ROOT / "docs" / "solution" / "README.md",
    ROOT / "competition" / "evidence" / "NUMBERS_MASTER.csv",
    ROOT / "competition" / "evidence" / "CLAIM_EVIDENCE.csv",
    LATEST / "classification_metrics.csv",
    LATEST / "ranking_metrics.csv",
    LATEST / "split_sensitivity_metrics.csv",
    LATEST / "split_sensitivity_summary.csv",
    LATEST / "run_manifest.json",
)

BANNED_PATTERNS = (
    "不是",
    "而是",
    "并非",
    "不只是",
    "不止",
    "是否",
    "有没有",
    "能不能",
)

METRIC_TOLERANCE = 5e-7


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str, findings: list[str]) -> None:
    if condition:
        findings.append(f"PASS  {message}")
        return
    raise AssertionError(message)


def section_length(markdown: str, heading: str) -> int:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## )", markdown)
    if match is None:
        raise AssertionError(f"missing section: {heading}")
    return len(match.group(1).strip())


def main() -> None:
    findings: list[str] = []
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED_FILES if not path.is_file()]
    require(not missing, "required competition artifacts are present", findings)

    application = (ROOT / "materials" / "APPLICATION_DRAFT.md").read_text(encoding="utf-8")
    require(section_length(application, "项目所属领域及细分方向（100 字以内）") <= 100,
            "competition direction stays within 100 characters", findings)
    require(section_length(application, "项目概述（500 字以内）") <= 500,
            "project overview stays within 500 characters", findings)

    scan_files = [
        ROOT / "README.md",
        ROOT / "CURRENT_STATE.md",
        ROOT / "materials" / "APPLICATION_DRAFT.md",
        ROOT / "materials" / "DEFENSE_DECK_OUTLINE.md",
        ROOT / "materials" / "DEMO_SCRIPT.md",
        *sorted((ROOT / "docs").glob("*.md")),
    ]
    language_hits: list[str] = []
    for path in scan_files:
        text = path.read_text(encoding="utf-8")
        for pattern in BANNED_PATTERNS:
            if pattern in text:
                language_hits.append(f"{path.relative_to(ROOT)}:{pattern}")
    require(not language_hits, "authored research materials pass the language screen", findings)

    primary_rows = read_csv(LATEST / "classification_metrics.csv")
    primary_30 = next(
        row for row in primary_rows
        if float(row["contamination"]) == 0.3 and row["method"] == "multi_evidence_logistic"
    )
    require(abs(float(primary_30["f1"]) - 0.7495073125194482) < METRIC_TOLERANCE,
            "primary 30% F1 matches the locked result", findings)
    require(abs(float(primary_30["auprc"]) - 0.9492221877817787) < METRIC_TOLERANCE,
            "primary 30% AUPRC matches the locked result", findings)

    sensitivity = read_csv(LATEST / "split_sensitivity_metrics.csv")
    levels = {float(row["contamination"]) for row in sensitivity}
    seeds = {int(row["split_seed"]) for row in sensitivity}
    require(len(sensitivity) == 25 and levels == {0.01, 0.05, 0.1, 0.2, 0.3} and len(seeds) == 5,
            "split sensitivity contains five levels by five contributor splits", findings)

    dashboard = json.loads((ROOT / "app" / "data" / "dashboard.json").read_text(encoding="utf-8"))
    headline = dashboard["headline"]
    require(abs(float(headline["risk_detection_f1_at_30pct"]) - float(primary_30["f1"])) < 1e-12,
            "product headline matches the primary result", findings)

    manifest = json.loads((LATEST / "run_manifest.json").read_text(encoding="utf-8"))
    require(manifest["run_status"] == "success" and manifest["code_version"] == "0.2.0",
            "run manifest records a successful version 0.2.0 execution", findings)
    for relative, expected in manifest["inputs"].items():
        require(sha256(ROOT / relative) == expected, f"input hash matches: {relative}", findings)
    for relative, expected in manifest["outputs"].items():
        require(sha256(ROOT / relative) == expected, f"output hash matches: {relative}", findings)

    print("\n".join(findings))
    print(f"PASS  competition package accepted ({len(findings)} checks)")


if __name__ == "__main__":
    main()
