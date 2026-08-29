"""Reusable entry point for assessing a caller-provided canonical dataset."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .features import extract_features
from .scoring import TierThresholds, score_records


REQUIRED_FIELDS = ("record_id", "entity_id", "rating")
OPTIONAL_FIELDS = (
    "contributor_id",
    "review_text",
    "created_at",
    "source",
    "version",
    "verification_level",
    "ai_disclosure",
    "account_age_days",
    "entity_reference_score",
    "cross_source_gap",
)


def prepare_canonical_records(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate required identifiers and add explicitly unavailable evidence fields."""
    if frame.empty:
        raise ValueError("Input dataset is empty")
    missing = [field for field in REQUIRED_FIELDS if field not in frame.columns]
    if missing:
        raise ValueError(f"Missing required canonical fields: {missing}")

    result = frame.copy()
    for field in ("record_id", "entity_id"):
        valid = result[field].notna() & result[field].astype(str).str.strip().ne("")
        if not valid.all():
            bad_rows = result.index[~valid].tolist()[:10]
            raise ValueError(f"Field {field!r} is blank at rows {bad_rows}")
    if result["record_id"].astype(str).duplicated().any():
        duplicates = (
            result.loc[result["record_id"].astype(str).duplicated(keep=False), "record_id"]
            .astype(str)
            .unique()
            .tolist()[:10]
        )
        raise ValueError(f"record_id must be unique; duplicates include {duplicates}")

    numeric_rating = pd.to_numeric(result["rating"], errors="coerce")
    invalid_rating = numeric_rating.isna() | ~numeric_rating.between(0, 5)
    if invalid_rating.any():
        bad_rows = result.index[invalid_rating].tolist()[:10]
        raise ValueError(
            "Canonical rating must be numeric and within 0-5; "
            f"invalid rows include {bad_rows}"
        )
    result["rating"] = numeric_rating.astype(float)

    for field in OPTIONAL_FIELDS:
        if field not in result.columns:
            result[field] = pd.NA
    return result


def _risk_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if float(row.get("evidence_coverage", 0) or 0) < 0.60:
        flags.append("INSUFFICIENT_EVIDENCE")
    dimensions = {
        "provenance_risk": "PROVENANCE_RISK",
        "behavior_risk": "BEHAVIOR_ANOMALY",
        "content_risk": "CONTENT_SIMILARITY_RISK",
        "cross_source_risk": "CROSS_SOURCE_DIVERGENCE",
        "temporal_risk": "TEMPORAL_BURST_RISK",
    }
    for field, code in dimensions.items():
        value = pd.to_numeric(pd.Series([row.get(field)]), errors="coerce").iloc[0]
        if pd.notna(value) and float(value) >= 0.60:
            flags.append(code)
    return "|".join(flags) if flags else "NONE"


def assess_records(
    frame: pd.DataFrame,
    config: dict[str, Any],
    scenario: str = "ranking_integrity",
) -> pd.DataFrame:
    """Generate advisory trust scores, tiers, flags, and governance actions."""
    scenarios = config.get("scenarios", {})
    if scenario not in scenarios:
        raise ValueError(f"Unknown scenario {scenario!r}; expected one of {sorted(scenarios)}")

    canonical = prepare_canonical_records(frame)
    features = extract_features(canonical)
    tier_config = config["tiers"]
    thresholds = TierThresholds(
        trusted=float(tier_config["trusted"]),
        standard=float(tier_config["standard"]),
        watch=float(tier_config["watch"]),
        review_required=float(tier_config["review_required"]),
    )
    scored = score_records(
        features,
        {key: float(value) for key, value in scenarios[scenario].items()},
        thresholds,
        minimum_weight=float(config["governance"]["minimum_weight"]),
    )
    scored.insert(1, "assessment_version", str(config["version"]))
    scored.insert(2, "assessment_scenario", scenario)
    scored["risk_flags"] = scored.apply(_risk_flags, axis=1)
    scored["decision_status"] = "advisory_pending_policy_or_human_review"
    return scored
