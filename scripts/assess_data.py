"""Assess a caller-provided CSV/JSON/JSONL/Parquet dataset with TrustData."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trustdata.assessment import assess_records
from trustdata.io import read_table, write_table


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate advisory TrustData scores and governance tiers for canonical records."
    )
    parser.add_argument("--input", required=True, type=Path, help="Input CSV/JSON/JSONL/Parquet")
    parser.add_argument("--output", required=True, type=Path, help="Scored output path")
    parser.add_argument(
        "--scenario",
        default="ranking_integrity",
        help="Scenario name defined under scenarios in configs/trust.yaml",
    )
    parser.add_argument(
        "--config", type=Path, default=ROOT / "configs" / "trust.yaml", help="TrustData YAML config"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    source = read_table(args.input)
    scored = assess_records(source, config, args.scenario)
    write_table(scored, args.output)

    summary = {
        "assessment_version": config["version"],
        "scenario": args.scenario,
        "input": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "records": int(len(scored)),
        "average_data_trust_score": float(scored["data_trust_score"].mean()),
        "tier_distribution": {
            str(key): int(value) for key, value in scored["tier"].value_counts().items()
        },
        "confidence_distribution": {
            str(key): int(value) for key, value in scored["confidence"].value_counts().items()
        },
        "review_queue_count": int(
            scored["recommended_action"].isin(["human_review", "temporary_restriction"]).sum()
        ),
        "evidence_boundary": (
            "Outputs are advisory data-use risk assessments. They do not establish user intent, "
            "content truth, legal liability, or production effectiveness without local calibration."
        ),
    }
    summary_path = args.output.with_name(f"{args.output.stem}.summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] assessed records={len(scored):,} scenario={args.scenario}")
    print(f"[OK] scored output={args.output}")
    print(f"[OK] summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
