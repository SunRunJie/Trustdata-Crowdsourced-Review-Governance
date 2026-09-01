"""Create normalized observed entity and text tables from the prior archives."""

from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trustdata.normalization import load_observed_entities, load_observed_reviews
from trustdata.io import write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare observed TrustData inputs.")
    parser.add_argument("--output", type=Path, default=None, help="Optional processed-data destination")
    return parser.parse_args()


def prepare_observed_data(output: Path | None = None) -> dict:
    prior = ROOT / "prior_research"
    output = output or ROOT / "data" / "processed"
    output.mkdir(parents=True, exist_ok=True)

    entities = load_observed_entities(prior)
    reviews = load_observed_reviews(prior)

    entity_path = output / "observed_entities.csv"
    review_path = output / "observed_reviews.csv"
    write_csv(entities, entity_path, encoding="utf-8-sig", sort_by=["record_id"])
    write_csv(reviews, review_path, encoding="utf-8-sig", sort_by=["record_id"])

    summary = {
        "entities_total": int(len(entities)),
        "entities_by_platform": {
            str(key): int(value) for key, value in entities["platform"].value_counts().items()
        },
        "unique_entity_ids": int(entities["entity_id"].nunique()),
        "cross_source_entities": int(entities["cross_source_gap"].notna().groupby(entities["entity_id"]).any().sum()),
        "reviews_total": int(len(reviews)),
        "review_exact_duplicates": int(reviews.duplicated(["review_text"]).sum()),
        "review_sources": int(reviews["contributor_id"].nunique()),
        "review_text_missing": int(reviews["review_text"].isna().sum()),
        "observed_rows_total": int(len(entities) + len(reviews)),
        "evidence_boundary": (
            "Observed archives support descriptive entity/content baselines; "
            "contributor-level longitudinal behavior belongs to the platform pilot dataset."
        ),
    }
    (output / "observed_data_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[OK] entities={len(entities):,} -> {entity_path}")
    print(f"[OK] reviews={len(reviews):,} -> {review_path}")
    return summary


def main() -> int:
    args = parse_args()
    summary = prepare_observed_data(args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["entities_total"] or not summary["reviews_total"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
