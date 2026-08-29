"""Create normalized observed entity and text tables from the prior archives."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trustdata.normalization import load_observed_entities, load_observed_reviews


def main() -> int:
    prior = ROOT / "prior_research"
    output = ROOT / "data" / "processed"
    output.mkdir(parents=True, exist_ok=True)

    entities = load_observed_entities(prior)
    reviews = load_observed_reviews(prior)

    entity_path = output / "observed_entities.csv"
    review_path = output / "observed_reviews.csv"
    entities.to_csv(entity_path, index=False, encoding="utf-8-sig")
    reviews.to_csv(review_path, index=False, encoding="utf-8-sig")

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
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if entities.empty or reviews.empty:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
