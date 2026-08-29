"""Coverage-aware Trust Vector, scenario score, tier, and governance output."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


DIMENSIONS = {
    "provenance": ("provenance_risk", "provenance_coverage", "P"),
    "behavior": ("behavior_risk", "behavior_coverage", "B"),
    "content": ("content_risk", "content_coverage", "C"),
    "cross_source": ("cross_source_risk", "cross_source_coverage", "X"),
    "temporal": ("temporal_risk", "temporal_coverage", "T"),
}


@dataclass(frozen=True)
class TierThresholds:
    trusted: float = 85
    standard: float = 70
    watch: float = 55
    review_required: float = 35


def score_records(
    features: pd.DataFrame,
    weights: dict[str, float],
    thresholds: TierThresholds = TierThresholds(),
    minimum_weight: float = 0.05,
) -> pd.DataFrame:
    result = features.copy()
    unknown = set(weights) - set(DIMENSIONS)
    if unknown:
        raise ValueError(f"Unknown trust dimensions: {sorted(unknown)}")
    if not np.isclose(sum(weights.values()), 1.0):
        raise ValueError("Scenario weights must sum to 1")

    weighted_integrity = pd.Series(0.0, index=result.index)
    observed_weight = pd.Series(0.0, index=result.index)
    integrity_values: list[pd.Series] = []
    for dimension, (risk_field, coverage_field, short) in DIMENSIONS.items():
        risk = pd.to_numeric(result[risk_field], errors="coerce")
        coverage = pd.to_numeric(result[coverage_field], errors="coerce").fillna(0).clip(0, 1)
        integrity = (100 * (1 - risk)).clip(0, 100)
        result[short] = integrity
        weight = float(weights.get(dimension, 0))
        available = risk.notna().astype(float)
        effective = weight * coverage * available
        weighted_integrity += integrity.fillna(0) * effective
        observed_weight += effective
        integrity_values.append(integrity)

    result["evidence_coverage"] = observed_weight.clip(0, 1)
    result["data_trust_score"] = (weighted_integrity / observed_weight.replace(0, np.nan)).clip(0, 100)
    result["dimension_disagreement"] = pd.concat(integrity_values, axis=1).std(axis=1, skipna=True).fillna(0)
    result["uncertainty"] = (
        70 * (1 - result["evidence_coverage"]) + 0.30 * result["dimension_disagreement"]
    ).clip(0, 100)
    result["confidence"] = np.select(
        [
            (result["evidence_coverage"] >= 0.85) & (result["uncertainty"] < 20),
            result["evidence_coverage"] >= 0.60,
        ],
        ["High", "Medium"],
        default="Low",
    )

    score = result["data_trust_score"].fillna(0)
    coverage = result["evidence_coverage"]
    result["tier"] = np.select(
        [
            (score >= thresholds.trusted) & (coverage >= 0.80),
            (score >= thresholds.standard) & (coverage >= 0.60),
            score >= thresholds.watch,
            score >= thresholds.review_required,
        ],
        ["A_Trusted", "B_Standard", "C_Watch", "D_Review_Required"],
        default="E_Restricted",
    )
    result["recommended_action"] = result["tier"].map(
        {
            "A_Trusted": "normal_use",
            "B_Standard": "normal_use_with_monitoring",
            "C_Watch": "downweight_and_monitor",
            "D_Review_Required": "human_review",
            "E_Restricted": "temporary_restriction",
        }
    )
    result["trust_weight"] = np.maximum(minimum_weight, (score / 100.0) ** 2)
    result["risk_score_rule"] = (1 - score / 100.0).clip(0, 1)
    return result

