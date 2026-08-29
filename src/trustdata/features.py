"""Interpretable provenance, behavior, content, cross-source, and temporal features."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


DIMENSION_RISKS = [
    "provenance_risk",
    "behavior_risk",
    "content_risk",
    "cross_source_risk",
    "temporal_risk",
]


def _present(series: pd.Series) -> pd.Series:
    return series.notna() & series.astype(str).str.strip().ne("")


def _robust_tail_risk(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0).astype(float)
    median = float(values.median())
    mad = float((values - median).abs().median())
    if mad > 1e-12:
        z = (values - median) / (1.4826 * mad)
        return pd.Series(1 / (1 + np.exp(-np.clip(z - 3.0, -30, 30))), index=series.index)
    upper = float(values.quantile(0.95))
    scale = max(1.0, upper - median)
    return ((values - median) / scale).clip(0, 1)


def _normalize_text(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace(r"[^a-z0-9\s]", "", regex=True)
        .str.strip()
    )


def _template_signature(value: str) -> str:
    text = re.sub(r"\d+", "#", value.lower())
    text = re.sub(r"\b(?:variant|version|copy)\s*#?\b", "template", text)
    text = re.sub(r"[^a-z#\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_features(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"record_id", "entity_id", "rating", "created_at"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing canonical fields: {sorted(missing)}")

    result = frame.copy()
    result["created_at_parsed"] = pd.to_datetime(result["created_at"], errors="coerce", utc=True)
    result["event_date"] = result["created_at_parsed"].dt.floor("D")

    provenance_fields = [
        "source",
        "contributor_id",
        "created_at",
        "version",
        "verification_level",
        "ai_disclosure",
    ]
    presence = []
    for field in provenance_fields:
        if field in result:
            presence.append(_present(result[field]).astype(float))
        else:
            presence.append(pd.Series(0.0, index=result.index))
    result["provenance_completeness"] = pd.concat(presence, axis=1).mean(axis=1)
    verified = result.get("verification_level", pd.Series(None, index=result.index)).astype("string")
    verification_factor = verified.isin(
        ["controlled_benchmark", "third_party_observed_archive", "platform_verified"]
    ).astype(float)
    result["provenance_risk"] = (
        1.0 - (0.8 * result["provenance_completeness"] + 0.2 * verification_factor)
    ).clip(0, 1)
    result["provenance_coverage"] = result["provenance_completeness"]

    contributor_key = result.get("contributor_id", pd.Series(None, index=result.index)).fillna(
        result["record_id"].map(lambda value: f"missing:{value}")
    )
    result["_contributor_key"] = contributor_key
    contributor_count = result.groupby("_contributor_key")["record_id"].transform("size")
    unique_entities = result.groupby("_contributor_key")["entity_id"].transform("nunique")
    active_days = result.groupby("_contributor_key")["event_date"].transform("nunique").clip(lower=1)
    daily = result.groupby(["_contributor_key", "event_date"])["record_id"].transform("size")
    max_daily = daily.groupby(result["_contributor_key"]).transform("max")
    extreme = (pd.to_numeric(result["rating"], errors="coerce") <= 1.0) | (
        pd.to_numeric(result["rating"], errors="coerce") >= 4.5
    )
    extreme_ratio = extreme.astype(float).groupby(result["_contributor_key"]).transform("mean")
    frequency_risk = _robust_tail_risk(contributor_count / active_days)
    burst_risk = _robust_tail_risk(max_daily)
    target_concentration = (1 - unique_entities / contributor_count.clip(lower=1)).clip(0, 1)
    account_age = pd.to_numeric(
        result.get("account_age_days", pd.Series(np.nan, index=result.index)), errors="coerce"
    )
    new_account_signal = ((30 - account_age) / 30).clip(0, 1).fillna(0)
    result["behavior_risk"] = (
        0.30 * frequency_risk
        + 0.25 * burst_risk
        + 0.25 * extreme_ratio
        + 0.15 * target_concentration
        + 0.05 * new_account_signal
    ).clip(0, 1)
    result["behavior_coverage"] = (
        _present(result.get("contributor_id", pd.Series(None, index=result.index))).astype(float)
        * 0.7
        + account_age.notna().astype(float) * 0.3
    )
    result["behavior_contribution_count"] = contributor_count
    result["behavior_burst_risk"] = burst_risk
    result["behavior_extreme_ratio"] = extreme_ratio
    result["new_account_signal"] = new_account_signal

    text = result.get("review_text", pd.Series(None, index=result.index))
    normalized = _normalize_text(text)
    has_text = normalized.ne("")
    exact_size = normalized.where(has_text).groupby(normalized.where(has_text)).transform("size")
    signatures = normalized.map(_template_signature)
    template_size = signatures.where(has_text).groupby(signatures.where(has_text)).transform("size")
    words = normalized.str.split()
    word_count = words.str.len().fillna(0)
    lexical_diversity = words.map(lambda values: len(set(values)) / len(values) if values else np.nan)
    result["content_exact_group_size"] = exact_size.fillna(0)
    result["content_template_group_size"] = template_size.fillna(0)
    duplicate_risk = (np.log1p(exact_size.fillna(0)) / np.log(20)).clip(0, 1)
    template_risk = (np.log1p(template_size.fillna(0)) / np.log(30)).clip(0, 1)
    short_risk = ((15 - word_count) / 15).clip(0, 1)
    low_diversity = ((0.45 - lexical_diversity) / 0.45).clip(0, 1).fillna(0)
    content_risk = (0.40 * duplicate_risk + 0.35 * template_risk + 0.15 * short_risk + 0.10 * low_diversity)
    result["content_risk"] = content_risk.where(has_text)
    result["content_coverage"] = has_text.astype(float)
    result["content_word_count"] = word_count
    result["content_lexical_diversity"] = lexical_diversity

    rating = pd.to_numeric(result["rating"], errors="coerce")
    reference = pd.to_numeric(
        result.get("entity_reference_score", pd.Series(np.nan, index=result.index)), errors="coerce"
    )
    source_gap = pd.to_numeric(
        result.get("cross_source_gap", pd.Series(np.nan, index=result.index)), errors="coerce"
    )
    deviation = ((rating - reference).abs() / 4.5).clip(0, 1)
    gap_risk = (source_gap / 2.0).clip(0, 1)
    result["cross_source_risk"] = (0.75 * deviation + 0.25 * gap_risk).where(
        reference.notna() & source_gap.notna()
    )
    result["cross_source_coverage"] = (reference.notna() & source_gap.notna()).astype(float)
    result["cross_source_rating_deviation"] = deviation

    entity_daily_count = result.groupby(["entity_id", "event_date"])["record_id"].transform("size")
    global_daily_count = result.groupby("event_date")["record_id"].transform("size")
    entity_burst = _robust_tail_risk(entity_daily_count)
    global_burst = _robust_tail_risk(global_daily_count)
    result["temporal_risk"] = (0.75 * entity_burst + 0.25 * global_burst).where(
        result["created_at_parsed"].notna()
    )
    result["temporal_coverage"] = result["created_at_parsed"].notna().astype(float)
    result["temporal_entity_day_count"] = entity_daily_count
    result["temporal_global_day_count"] = global_daily_count

    result = result.drop(columns=["_contributor_key"])
    return result

