"""Create a compact deterministic seed for fresh-clone demonstrations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .io import write_csv
from .normalization import stable_id


def ensure_demo_seed(
    processed: Path,
    *,
    entity_count: int,
    review_count: int = 1_000,
    random_seed: int,
) -> bool:
    """Create deterministic E2 inputs when no external processed data is present."""
    entity_path = processed / "observed_entities.csv"
    review_path = processed / "observed_reviews.csv"
    summary_path = processed / "observed_data_summary.json"
    if entity_path.is_file() and review_path.is_file() and summary_path.is_file():
        return False

    processed.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(random_seed)
    entity_count = max(100, int(entity_count))
    review_count = max(100, int(review_count))

    entity_ids = [stable_id("bundled-demo-entity", index, prefix="entity") for index in range(entity_count)]
    reference_scores = np.clip(np.round(rng.normal(3.55, 0.72, entity_count) * 20) / 20, 0.5, 5.0)
    entities = pd.DataFrame(
        {
            "record_id": [stable_id("bundled-demo-record", index, prefix="entity_record") for index in range(entity_count)],
            "entity_id": entity_ids,
            "platform": "bundled_demo_seed",
            "rating": reference_scores,
            "rating_count": rng.integers(25, 25_000, size=entity_count),
            "cross_source_reference": reference_scores,
            "cross_source_gap": np.round(rng.uniform(0.02, 0.65, size=entity_count), 4),
            "source": "deterministic_bundled_generator",
            "verification_level": "E2_controlled_synthetic_seed",
            "is_synthetic": True,
        }
    )

    adjectives = ("balanced", "vivid", "restrained", "layered", "direct", "subtle", "dynamic", "focused")
    aspects = ("arrangement", "production", "pacing", "melody", "rhythm", "texture", "performance", "structure")
    reviews = pd.DataFrame(
        {
            "record_id": [stable_id("bundled-demo-review", index, prefix="review") for index in range(review_count)],
            "entity_id": [entity_ids[index % entity_count] for index in range(review_count)],
            "contributor_id": [stable_id("demo-contributor", index % 137, prefix="contributor") for index in range(review_count)],
            "rating": [float(reference_scores[index % entity_count]) for index in range(review_count)],
            "review_text": [
                f"A {adjectives[index % len(adjectives)]} assessment of the {aspects[(index // len(adjectives)) % len(aspects)]}; controlled sample {index:04d}."
                for index in range(review_count)
            ],
            "source": "deterministic_bundled_generator",
            "verification_level": "E2_controlled_synthetic_seed",
            "is_synthetic": True,
        }
    )

    write_csv(entities, entity_path, encoding="utf-8-sig", sort_by=["record_id"])
    write_csv(reviews, review_path, encoding="utf-8-sig", sort_by=["record_id"])
    summary = {
        "entities_total": entity_count,
        "entities_by_platform": {"bundled_demo_seed": entity_count},
        "unique_entity_ids": entity_count,
        "cross_source_entities": entity_count,
        "reviews_total": review_count,
        "review_exact_duplicates": 0,
        "review_sources": 137,
        "review_text_missing": 0,
        "observed_rows_total": entity_count + review_count,
        "evidence_boundary": (
            "Bundled E2 synthetic seed for deterministic demonstration and CI only; "
            "external platform conclusions require independently sourced and documented data."
        ),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
