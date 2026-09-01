"""Classification, calibration, ablation, fairness, and ranking evaluation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    ndcg_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedGroupKFold


MODEL_FEATURES = [
    "provenance_risk",
    "behavior_risk",
    "content_risk",
    "cross_source_risk",
    "temporal_risk",
    "provenance_coverage",
    "behavior_coverage",
    "content_coverage",
    "cross_source_coverage",
    "temporal_coverage",
]


@dataclass
class FittedRiskModel:
    pipeline: Pipeline
    threshold: float
    features: list[str]

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        matrix = frame[self.features].fillna(-1.0)
        return self.pipeline.predict_proba(matrix)[:, 1]


def _bucket(value: object) -> int:
    digest = hashlib.sha256(str(value).encode("utf-8")).digest()
    return int.from_bytes(digest[:2], "big") % 10


def split_mask(frame: pd.DataFrame) -> pd.Series:
    if "evaluation_split" in frame:
        return frame["evaluation_split"].astype(str)
    key = frame["contributor_id"].fillna(frame["record_id"])
    bucket = key.map(_bucket)
    return pd.Series(np.select([bucket <= 5, bucket <= 7], ["train", "validation"], default="test"), index=frame.index)


def balanced_group_split_map(
    frame: pd.DataFrame,
    random_state: int = 20260828,
) -> dict[str, str]:
    """Build one stable, class-balanced, contributor-disjoint split map."""
    ordered = frame.sort_values("record_id", kind="mergesort").reset_index(drop=True)
    groups = ordered["contributor_id"].fillna(ordered["record_id"]).astype(str)
    truth = ordered["ground_truth_risk"].astype(int)
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=random_state)
    assignment = np.full(len(frame), "", dtype=object)
    fold_names = ["test", "validation", "train", "train", "train"]
    placeholder = np.zeros((len(frame), 1))
    for fold, (_, test_index) in enumerate(splitter.split(placeholder, truth, groups)):
        assignment[test_index] = fold_names[fold]
    if (assignment == "").any():
        raise RuntimeError("Incomplete evaluation split assignment")
    return dict(zip(ordered["record_id"].astype(str), assignment, strict=True))


def _top_entity_ids(frame: pd.DataFrame, score: str, count: int) -> set[object]:
    """Select top entities deterministically when scores are tied."""
    ordered = frame[[score]].copy()
    ordered["_entity_key"] = ordered.index.map(str)
    ordered = ordered.sort_values(
        [score, "_entity_key"], ascending=[False, True], kind="mergesort"
    )
    return set(ordered.head(count).index)


def expected_calibration_error(y_true: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    value = 0.0
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (probability >= lower) & (probability < upper if upper < 1 else probability <= upper)
        if mask.any():
            value += mask.mean() * abs(float(y_true[mask].mean()) - float(probability[mask].mean()))
    return float(value)


def choose_threshold(
    y_true: np.ndarray,
    probability: np.ndarray,
    maximum_false_positive_rate: float = 0.01,
) -> float:
    candidates = np.linspace(0.10, 0.90, 81)
    feasible: list[tuple[float, float]] = []
    truth = np.asarray(y_true, dtype=int)
    for value in candidates:
        prediction = probability >= value
        negatives = truth == 0
        fpr = float(prediction[negatives].mean()) if negatives.any() else 0.0
        if fpr <= maximum_false_positive_rate:
            feasible.append((float(f1_score(truth, prediction, zero_division=0)), float(value)))
    if not feasible:
        return 0.90
    return max(feasible, key=lambda pair: (pair[0], pair[1]))[1]


def classification_metrics(
    y_true: pd.Series | np.ndarray,
    probability: pd.Series | np.ndarray,
    threshold: float,
) -> dict[str, float | int]:
    truth = np.asarray(y_true, dtype=int)
    score = np.asarray(probability, dtype=float)
    prediction = (score >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(truth, prediction, labels=[0, 1]).ravel()
    metrics: dict[str, float | int] = {
        "n": int(len(truth)),
        "positives": int(truth.sum()),
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(truth, prediction)),
        "precision": float(precision_score(truth, prediction, zero_division=0)),
        "recall": float(recall_score(truth, prediction, zero_division=0)),
        "f1": float(f1_score(truth, prediction, zero_division=0)),
        "fpr": float(fp / (fp + tn)) if fp + tn else 0.0,
        "fnr": float(fn / (fn + tp)) if fn + tp else 0.0,
        "brier": float(brier_score_loss(truth, score)),
        "ece": expected_calibration_error(truth, score),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }
    if len(np.unique(truth)) == 2:
        metrics["auroc"] = float(roc_auc_score(truth, score))
        metrics["auprc"] = float(average_precision_score(truth, score))
    else:
        metrics["auroc"] = float("nan")
        metrics["auprc"] = float("nan")
    return metrics


def fit_risk_model(
    frame: pd.DataFrame,
    features: list[str] | None = None,
    *,
    random_state: int = 20260828,
    maximum_false_positive_rate: float = 0.01,
) -> FittedRiskModel:
    chosen = features or MODEL_FEATURES
    split = split_mask(frame)
    train = split.eq("train")
    validation = split.eq("validation")
    pipeline = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=random_state,
                    C=0.8,
                ),
            ),
        ]
    )
    pipeline.fit(frame.loc[train, chosen].fillna(-1.0), frame.loc[train, "ground_truth_risk"])
    validation_probability = pipeline.predict_proba(frame.loc[validation, chosen].fillna(-1.0))[:, 1]
    threshold = choose_threshold(
        frame.loc[validation, "ground_truth_risk"].to_numpy(),
        validation_probability,
        maximum_false_positive_rate=maximum_false_positive_rate,
    )
    return FittedRiskModel(pipeline=pipeline, threshold=threshold, features=list(chosen))


def evaluate_methods(frame: pd.DataFrame, model: FittedRiskModel) -> tuple[pd.DataFrame, np.ndarray]:
    split = split_mask(frame)
    test = split.eq("test")
    truth = frame.loc[test, "ground_truth_risk"]
    simple = (
        (frame["provenance_risk"] > 0.45)
        | ((frame["new_account_signal"] > 0.8) & (frame["behavior_extreme_ratio"] > 0.75))
    ).astype(float)
    probabilities = {
        "no_filter": np.zeros(len(frame)),
        "simple_rule": simple.to_numpy(float),
        "behavior_only": frame["behavior_risk"].fillna(0.5).to_numpy(float),
        "content_only": frame["content_risk"].fillna(0.0).to_numpy(float),
        "rule_fusion": frame["risk_score_rule"].fillna(0.5).to_numpy(float),
        "multi_evidence_logistic": model.predict_proba(frame),
    }
    rows: list[dict[str, float | int | str]] = []
    for name, probability in probabilities.items():
        threshold = model.threshold if name == "multi_evidence_logistic" else 0.5
        row: dict[str, float | int | str] = {"method": name}
        row.update(classification_metrics(truth, probability[test.to_numpy()], threshold))
        rows.append(row)
    return pd.DataFrame(rows), probabilities["multi_evidence_logistic"]


def ranking_metrics(
    clean: pd.DataFrame,
    contaminated: pd.DataFrame,
    risk_probability: np.ndarray,
    review_threshold: float,
) -> dict[str, float]:
    clean_rank = clean.groupby("entity_id", as_index=True)["rating"].mean().rename("clean")
    raw = contaminated.groupby("entity_id", as_index=True)["rating"].mean().rename("raw")
    weighted_input = contaminated[["entity_id", "rating"]].copy()
    weighted_input["weight"] = np.where(
        risk_probability >= review_threshold,
        np.maximum(0.05, (1 - risk_probability) ** 2),
        1.0,
    )
    weighted = (
        weighted_input.assign(weighted_rating=lambda data: data["rating"] * data["weight"])
        .groupby("entity_id")[["weighted_rating", "weight"]]
        .sum()
    )
    weighted["weighted"] = weighted["weighted_rating"] / weighted["weight"].clip(lower=1e-9)
    joined = pd.concat([clean_rank, raw, weighted["weighted"]], axis=1).dropna()
    if len(joined) < 3:
        raise ValueError("Insufficient entities for ranking evaluation")

    clean_order = joined["clean"].rank(ascending=False, method="average")
    raw_order = joined["raw"].rank(ascending=False, method="average")
    weighted_order = joined["weighted"].rank(ascending=False, method="average")
    top_k = min(100, len(joined))
    clean_top = _top_entity_ids(joined, "clean", top_k)
    raw_top = _top_entity_ids(joined, "raw", top_k)
    weighted_top = _top_entity_ids(joined, "weighted", top_k)
    relevance = joined["clean"].to_numpy()[None, :]
    return {
        "entities": int(len(joined)),
        "raw_spearman": float(spearmanr(joined["clean"], joined["raw"]).statistic),
        "weighted_spearman": float(spearmanr(joined["clean"], joined["weighted"]).statistic),
        "raw_kendall": float(kendalltau(joined["clean"], joined["raw"]).statistic),
        "weighted_kendall": float(kendalltau(joined["clean"], joined["weighted"]).statistic),
        "raw_topk_overlap": float(len(clean_top & raw_top) / top_k),
        "weighted_topk_overlap": float(len(clean_top & weighted_top) / top_k),
        "raw_mean_rank_error": float((clean_order - raw_order).abs().mean()),
        "weighted_mean_rank_error": float((clean_order - weighted_order).abs().mean()),
        "raw_ndcg": float(ndcg_score(relevance, joined["raw"].to_numpy()[None, :])),
        "weighted_ndcg": float(ndcg_score(relevance, joined["weighted"].to_numpy()[None, :])),
    }


def ablation_study(
    frame: pd.DataFrame,
    *,
    random_state: int = 20260828,
    maximum_false_positive_rate: float = 0.01,
) -> pd.DataFrame:
    split = split_mask(frame)
    test = split.eq("test")
    rows: list[dict[str, float | int | str]] = []
    groups = {
        "full": MODEL_FEATURES,
        "without_provenance": [field for field in MODEL_FEATURES if not field.startswith("provenance")],
        "without_behavior": [field for field in MODEL_FEATURES if not field.startswith("behavior")],
        "without_content": [field for field in MODEL_FEATURES if not field.startswith("content")],
        "without_cross_source": [field for field in MODEL_FEATURES if not field.startswith("cross_source")],
        "without_temporal": [field for field in MODEL_FEATURES if not field.startswith("temporal")],
    }
    for name, fields in groups.items():
        model = fit_risk_model(
            frame,
            fields,
            random_state=random_state,
            maximum_false_positive_rate=maximum_false_positive_rate,
        )
        probability = model.predict_proba(frame)
        row: dict[str, float | int | str] = {"ablation": name}
        row.update(
            classification_metrics(
                frame.loc[test, "ground_truth_risk"], probability[test.to_numpy()], model.threshold
            )
        )
        rows.append(row)
    return pd.DataFrame(rows)


def fairness_audit(frame: pd.DataFrame, probability: np.ndarray, threshold: float) -> pd.DataFrame:
    clean = frame["ground_truth_risk"].eq(0)
    account_age = pd.to_numeric(frame["account_age_days"], errors="coerce")
    group = pd.cut(
        account_age,
        bins=[-np.inf, 30, 180, 730, np.inf],
        labels=["0-30", "31-180", "181-730", "731+"],
    )
    prediction = probability >= threshold
    rows = []
    for label in group.dropna().unique():
        mask = clean & group.eq(label)
        rows.append(
            {
                "account_age_group": str(label),
                "clean_n": int(mask.sum()),
                "false_positive_rate": float(prediction[mask.to_numpy()].mean()) if mask.any() else float("nan"),
            }
        )
    return pd.DataFrame(rows).sort_values("account_age_group")
