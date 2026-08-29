"""Controlled contamination benchmark seeded by observed music archives."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .normalization import stable_id


ATTACK_TYPES = (
    "rating_manipulation",
    "coordinated_accounts",
    "duplicate_content",
    "temporal_burst",
    "provenance_missing",
)


@dataclass(frozen=True)
class BenchmarkSpec:
    clean_records: int = 100_000
    contributors: int = 8_000
    entities: int = 2_000
    days: int = 180
    max_contamination: float = 0.30
    review_probability: float = 0.20
    random_seed: int = 20260828


def _choose_catalog(entities: pd.DataFrame, count: int) -> pd.DataFrame:
    catalog = (
        entities.loc[entities["cross_source_reference"].notna()]
        .sort_values(["entity_id", "rating_count"], ascending=[True, False])
        .drop_duplicates("entity_id")
        .copy()
    )
    catalog["reference_score"] = catalog["cross_source_reference"].clip(0.5, 5)
    catalog["attention_weight"] = np.sqrt(catalog["rating_count"].fillna(1).clip(lower=1))
    catalog = catalog.sort_values("attention_weight", ascending=False).head(count)
    if len(catalog) < min(100, count):
        raise ValueError("Insufficient cross-source entities for the benchmark")
    return catalog.reset_index(drop=True)


def _base_rows(
    catalog: pd.DataFrame,
    reviews: pd.DataFrame,
    spec: BenchmarkSpec,
    rng: np.random.Generator,
) -> pd.DataFrame:
    n = spec.clean_records
    entity_probability = catalog["attention_weight"].to_numpy(dtype=float, copy=True)
    entity_probability /= entity_probability.sum()
    entity_index = rng.choice(len(catalog), size=n, p=entity_probability)

    ranks = np.minimum(rng.zipf(1.45, size=n), spec.contributors) - 1
    contributors = np.array([f"control_user_{value:05d}" for value in ranks], dtype=object)
    contributor_bias_values = rng.normal(0, 0.18, size=spec.contributors)
    contributor_bias = contributor_bias_values[ranks]

    selected = catalog.iloc[entity_index].reset_index(drop=True)
    ratings = selected["reference_score"].to_numpy(float) + contributor_bias + rng.normal(0, 0.55, n)
    ratings = np.clip(np.round(ratings * 2) / 2, 0.5, 5.0)
    days = rng.integers(0, spec.days, size=n)
    seconds = rng.integers(0, 86_400, size=n)
    created_at = pd.Timestamp("2026-01-01", tz="UTC") + pd.to_timedelta(days, unit="D") + pd.to_timedelta(seconds, unit="s")

    contributor_age = np.clip(rng.lognormal(mean=6.2, sigma=1.0, size=spec.contributors), 3, 5000)
    new_account_indices = rng.choice(
        spec.contributors, size=max(1, int(round(spec.contributors * 0.10))), replace=False
    )
    contributor_age[new_account_indices] = rng.integers(1, 31, size=len(new_account_indices))
    account_age = contributor_age[ranks].round().astype(int)

    review_mask = rng.random(n) < spec.review_probability
    texts = np.full(n, None, dtype=object)
    available = reviews["review_text"].dropna().astype(str).drop_duplicates().to_numpy()
    review_indices = np.flatnonzero(review_mask)
    if len(review_indices):
        sampled = rng.choice(available, size=len(review_indices), replace=len(review_indices) > len(available))
        texts[review_indices] = sampled

    frame = pd.DataFrame(
        {
            "record_id": [stable_id("clean", index, prefix="benchmark") for index in range(n)],
            "platform": "controlled_music_benchmark",
            "entity_id": selected["entity_id"].to_numpy(),
            "entity_type": "music_album",
            "contributor_id": contributors,
            "rating": ratings,
            "review_text": texts,
            "created_at": created_at.astype(str),
            "updated_at": created_at.astype(str),
            "source": "controlled_real_distribution_seed",
            "ai_disclosure": "unknown",
            "verification_level": "controlled_benchmark",
            "version": "benchmark_v0.1.0",
            "account_age_days": account_age,
            "entity_reference_score": selected["reference_score"].to_numpy(),
            "cross_source_gap": selected["cross_source_gap"].to_numpy(),
            "is_synthetic": True,
            "ground_truth_risk": 0,
            "attack_type": "none",
            "attack_order": -1,
            "benchmark_role": "clean_control",
        }
    )
    return frame


def _attack_rows(
    catalog: pd.DataFrame,
    reviews: pd.DataFrame,
    spec: BenchmarkSpec,
    rng: np.random.Generator,
) -> pd.DataFrame:
    total = int(round(spec.clean_records * spec.max_contamination))
    per_type = total // len(ATTACK_TYPES)
    counts = [per_type] * len(ATTACK_TYPES)
    counts[-1] += total - sum(counts)
    targets = catalog.nlargest(min(100, len(catalog)), "attention_weight").reset_index(drop=True)
    texts = reviews["review_text"].dropna().astype(str).drop_duplicates().to_numpy()
    templates = rng.choice(texts, size=min(80, len(texts)), replace=False)
    parts: list[pd.DataFrame] = []

    for attack_index, (attack_type, count) in enumerate(zip(ATTACK_TYPES, counts, strict=True)):
        target_index = rng.integers(0, len(targets), size=count)
        selected = targets.iloc[target_index].reset_index(drop=True)
        cohort_size = max(20, count // 10)
        cohort = rng.integers(0, cohort_size, size=count)
        contributor = np.array(
            [f"risk_{attack_type}_{value:04d}" for value in cohort], dtype=object
        )
        event_days = rng.integers(0, spec.days, size=count)
        event_seconds = rng.integers(0, 86_400, size=count)
        created = pd.Timestamp("2026-01-01", tz="UTC") + pd.to_timedelta(event_days, unit="D") + pd.to_timedelta(event_seconds, unit="s")
        rating = np.where(rng.random(count) < 0.72, 5.0, 0.5)
        review_text = np.full(count, None, dtype=object)
        source = np.full(count, "controlled_injection", dtype=object)
        verification = np.full(count, "controlled_benchmark", dtype=object)
        ai_disclosure = np.full(count, "unknown", dtype=object)

        account_age = rng.integers(180, 3000, size=count)
        if attack_type == "duplicate_content":
            chosen = rng.choice(templates, size=count, replace=True)
            variant = rng.integers(0, 6, size=count)
            review_text = np.array(
                [f"{text} [template variant {number}]" for text, number in zip(chosen, variant, strict=True)],
                dtype=object,
            )
            rating = np.clip(
                np.round((selected["reference_score"].to_numpy() + rng.normal(0, 0.4, count)) * 2) / 2,
                0.5,
                5.0,
            )
        elif attack_type == "provenance_missing":
            source[:] = None
            verification[:] = None
            ai_disclosure[:] = None
            contributor[:] = [None if value % 2 == 0 else contributor[value] for value in range(count)]
            rating = np.clip(
                np.round((selected["reference_score"].to_numpy() + rng.normal(0, 0.65, count)) * 2) / 2,
                0.5,
                5.0,
            )
        elif attack_type == "temporal_burst":
            burst_days = rng.integers(spec.days - 7, spec.days, size=count)
            burst_seconds = rng.integers(0, 10_800, size=count)
            created = pd.Timestamp("2026-01-01", tz="UTC") + pd.to_timedelta(burst_days, unit="D") + pd.to_timedelta(burst_seconds, unit="s")
            contributor = np.array(
                [f"temporal_user_{value:05d}" for value in np.arange(count) % max(1, count // 2)],
                dtype=object,
            )
            rating = np.clip(
                np.round((selected["reference_score"].to_numpy() + rng.normal(0, 0.45, count)) * 2) / 2,
                0.5,
                5.0,
            )
        elif attack_type == "coordinated_accounts":
            selected = targets.iloc[cohort % min(20, len(targets))].reset_index(drop=True)
            account_age = rng.integers(0, 15, size=count)

        part = pd.DataFrame(
            {
                "record_id": [
                    stable_id(attack_type, index, prefix="injected") for index in range(count)
                ],
                "platform": "controlled_music_benchmark",
                "entity_id": selected["entity_id"].to_numpy(),
                "entity_type": "music_album",
                "contributor_id": contributor,
                "rating": rating,
                "review_text": review_text,
                "created_at": created.astype(str),
                "updated_at": created.astype(str),
                "source": source,
                "ai_disclosure": ai_disclosure,
                "verification_level": verification,
                "version": "benchmark_v0.1.0",
                "account_age_days": account_age,
                "entity_reference_score": selected["reference_score"].to_numpy(),
                "cross_source_gap": selected["cross_source_gap"].to_numpy(),
                "is_synthetic": True,
                "ground_truth_risk": 1,
                "attack_type": attack_type,
                "attack_order": np.arange(count),
                "benchmark_role": "controlled_injection",
            }
        )
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def generate_benchmark(
    entities: pd.DataFrame,
    reviews: pd.DataFrame,
    spec: BenchmarkSpec,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(spec.random_seed)
    catalog = _choose_catalog(entities, spec.entities)
    clean = _base_rows(catalog, reviews, spec, rng)
    attacks = _attack_rows(catalog, reviews, spec, rng)
    return clean, attacks, catalog


def subset_for_level(clean: pd.DataFrame, attacks: pd.DataFrame, level: float) -> pd.DataFrame:
    desired = int(round(len(clean) * level))
    selected_parts: list[pd.DataFrame] = []
    counts = attacks["attack_type"].value_counts()
    proportions = counts / counts.sum()
    for attack_type, proportion in proportions.items():
        take = int(round(desired * float(proportion)))
        selected_parts.append(
            attacks.loc[attacks["attack_type"] == attack_type].nsmallest(take, "attack_order")
        )
    selected = pd.concat(selected_parts, ignore_index=True)
    if len(selected) > desired:
        selected = selected.iloc[:desired].copy()
    elif len(selected) < desired:
        remaining = attacks.loc[~attacks["record_id"].isin(selected["record_id"])]
        selected = pd.concat([selected, remaining.nsmallest(desired - len(selected), "attack_order")])
    return pd.concat([clean, selected], ignore_index=True)
