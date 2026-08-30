"""Fail-fast end-to-end TrustData benchmark and product-data pipeline."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd
import yaml

from .benchmark import BenchmarkSpec, generate_benchmark, subset_for_level
from .evaluation import (
    ablation_study,
    balanced_group_split_map,
    evaluate_methods,
    fairness_audit,
    fit_risk_model,
    ranking_metrics,
)
from .features import extract_features
from .scoring import TierThresholds, score_records


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if pd.isna(value):
        return None
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")


def _write_dashboard_script(path: Path, payload: Any) -> None:
    """Write a browser-safe fallback so the demonstration also works from file://."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(_json_safe(payload), ensure_ascii=False, separators=(",", ":"))
    path.write_text(f"window.TRUSTDATA_DASHBOARD = {serialized};\n", encoding="utf-8")


def _sync_evidence_mirror(root: Path, output: Path) -> int:
    """Copy completed run artifacts to the versioned competition evidence mirror."""
    evidence = root / "competition" / "evidence"
    destinations = {
        "results": evidence / "results",
        "figures": evidence / "figures",
        "runtime": evidence / "runtime",
    }
    for destination in destinations.values():
        destination.mkdir(parents=True, exist_ok=True)

    sources = [
        *(path for path in output.glob("*.csv") if path.is_file()),
        *(path for path in output.glob("*.json") if path.name != "run_manifest.json" and path.is_file()),
        *(path for path in (output / "figures").glob("*") if path.is_file()),
    ]
    copied = 0
    for source in sources:
        destination_dir = destinations["figures"] if source.parent.name == "figures" else destinations["results"]
        shutil.copyfile(source, destination_dir / source.name)
        copied += 1
    shutil.copyfile(output / "run_manifest.json", destinations["runtime"] / "run_manifest.json")
    return copied + 1


def _build_training_frame(
    level_frames: dict[float, pd.DataFrame],
    levels: list[float],
    random_seed: int,
) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for level in levels:
        scored = level_frames[level]
        clean = scored.loc[scored["ground_truth_risk"].eq(0)].sample(
            n=min(20_000, int(scored["ground_truth_risk"].eq(0).sum())),
            random_state=int(random_seed + round(level * 1000)),
        )
        parts.append(
            pd.concat([clean, scored.loc[scored["ground_truth_risk"].eq(1)]], ignore_index=True)
        )
    return pd.concat(parts, ignore_index=True)


def _split_sensitivity_study(
    level_frames: dict[float, pd.DataFrame],
    levels: list[float],
    split_seeds: list[int],
    maximum_false_positive_rate: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, Any]] = []
    split_source = level_frames[max(levels)]
    for split_seed in split_seeds:
        split_map = balanced_group_split_map(split_source, random_state=split_seed)
        seeded_frames: dict[float, pd.DataFrame] = {}
        for level in levels:
            current = level_frames[level].copy()
            current["evaluation_split"] = current["record_id"].map(split_map)
            if current["evaluation_split"].isna().any():
                raise RuntimeError(f"Sensitivity split map is incomplete for seed {split_seed}")
            seeded_frames[level] = current
        training_frame = _build_training_frame(seeded_frames, levels, split_seed)
        model = fit_risk_model(
            training_frame,
            random_state=split_seed,
            maximum_false_positive_rate=maximum_false_positive_rate,
        )
        for level in levels:
            methods, _ = evaluate_methods(seeded_frames[level], model)
            primary = methods.loc[methods["method"].eq("multi_evidence_logistic")].iloc[0].to_dict()
            rows.append({"split_seed": split_seed, "contamination": level, **primary})

    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby("contamination", as_index=False)
        .agg(
            split_runs=("split_seed", "nunique"),
            threshold_median=("threshold", "median"),
            f1_median=("f1", "median"),
            f1_min=("f1", "min"),
            f1_max=("f1", "max"),
            auprc_median=("auprc", "median"),
            auprc_min=("auprc", "min"),
            auprc_max=("auprc", "max"),
            fpr_median=("fpr", "median"),
            fpr_min=("fpr", "min"),
            fpr_max=("fpr", "max"),
        )
        .sort_values("contamination")
    )
    return detail, summary


def _style_axis(ax: plt.Axes) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(direction="in", length=4, width=0.8, colors="#102A2A")
    ax.grid(True, linestyle=(0, (3, 4)), linewidth=0.7, alpha=0.28, color="#657B78")
    ax.set_axisbelow(True)


def _plot_results(
    output: Path,
    headline: pd.DataFrame,
    ablation: pd.DataFrame,
    scored: pd.DataFrame,
) -> list[Path]:
    figure_dir = output / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "savefig.dpi": 320,
            "font.family": "serif",
            "font.serif": ["Times New Roman"],
            "font.size": 10.5,
            "axes.titlesize": 13,
            "axes.labelsize": 11.5,
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "axes.unicode_minus": False,
        }
    )

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    proposed = headline.loc[headline["method"].eq("multi_evidence_logistic")].sort_values("contamination")
    simple = headline.loc[headline["method"].eq("simple_rule")].sort_values("contamination")
    ax.plot(proposed["contamination"], proposed["f1"], marker="o", linewidth=2.2, color="#0C5B4D", label="Multi-evidence F1")
    ax.plot(proposed["contamination"], proposed["auprc"], marker="s", linewidth=2.0, linestyle="--", color="#A96F28", label="Multi-evidence AUPRC")
    ax.plot(simple["contamination"], simple["f1"], marker="^", linewidth=1.6, color="#315F77", label="Simple-rule F1")
    ax.set(xlabel="Controlled contamination level", ylabel="Score", ylim=(0, 1.02))
    ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_title("Detection performance under controlled contamination")
    _style_axis(ax)
    ax.legend(frameon=False, ncol=1, loc="lower right")
    path = figure_dir / "risk_detection_by_contamination.png"
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig); paths.append(path)

    ranking = headline.drop_duplicates("contamination")
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.2))
    axes[0].plot(ranking["contamination"], ranking["raw_mean_rank_error"], marker="o", linewidth=1.8, color="#657B78", label="Raw")
    axes[0].plot(ranking["contamination"], ranking["weighted_mean_rank_error"], marker="o", linewidth=2.2, color="#0C5B4D", label="Trust-weighted")
    axes[0].set(xlabel="Contamination", ylabel="Mean rank error", title="Tail displacement (lower is better)")
    axes[1].plot(ranking["contamination"], ranking["raw_topk_overlap"], marker="o", linewidth=1.8, color="#657B78", label="Raw")
    axes[1].plot(ranking["contamination"], ranking["weighted_topk_overlap"], marker="o", linewidth=2.2, color="#0C5B4D", label="Trust-weighted")
    axes[1].set(xlabel="Contamination", ylabel="Top-100 overlap", title="Top-list retention (higher is better)", ylim=(0.55, 1.0))
    for ax in axes:
        ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
        _style_axis(ax)
    axes[0].legend(frameon=False, loc="upper left")
    axes[1].legend(frameon=False, loc="lower left")
    fig.suptitle("Ranking robustness by operating condition", fontsize=13.5, y=1.02)
    path = figure_dir / "ranking_robustness.png"
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig); paths.append(path)

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ordered = ablation.sort_values("f1")
    labels = {
        "full": "All dimensions",
        "without_provenance": "Without P",
        "without_behavior": "Without B",
        "without_content": "Without C",
        "without_cross_source": "Without X",
        "without_temporal": "Without T",
    }
    colors = ["#0C5B4D" if name == "full" else "#315F77" for name in ordered["ablation"]]
    bars = ax.barh(ordered["ablation"].map(labels), ordered["f1"], color=colors, height=0.62)
    ax.set(xlabel="F1 on held-out contributor groups", xlim=(0, 1.02))
    ax.set_title("Dimension ablation at 30% controlled contamination")
    _style_axis(ax)
    ax.grid(False, axis="y")
    ax.bar_label(bars, fmt="%.3f", padding=4, fontsize=9, color="#102A2A")
    path = figure_dir / "ablation_f1.png"
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig); paths.append(path)

    tier_counts = scored["tier"].value_counts().reindex(
        ["A_Trusted", "B_Standard", "C_Watch", "D_Review_Required", "E_Restricted"], fill_value=0
    )
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    bars = ax.bar(["A", "B", "C", "D", "E"], tier_counts.values, color=["#0C5B4D", "#315F77", "#A96F28", "#92473D", "#5D5650"], width=0.66)
    ax.set(ylabel="Records", title="Trust tier distribution (30% controlled contamination)")
    _style_axis(ax)
    ax.grid(False, axis="x")
    ax.bar_label(bars, fmt="%d", padding=4, fontsize=9, color="#102A2A")
    path = figure_dir / "tier_distribution.png"
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig); paths.append(path)
    return paths


def run_pipeline(root: Path, config_path: Path) -> dict[str, Any]:
    started = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    output = root / "outputs" / "runs" / "latest"
    output.mkdir(parents=True, exist_ok=True)
    processed = root / "data" / "processed"
    entity_path = processed / "observed_entities.csv"
    review_path = processed / "observed_reviews.csv"
    if not entity_path.exists() or not review_path.exists():
        raise FileNotFoundError("Run scripts/prepare_observed_data.py before the TrustData pipeline")

    entities = pd.read_csv(entity_path, encoding="utf-8-sig")
    reviews = pd.read_csv(review_path, encoding="utf-8-sig")
    benchmark_config = config["benchmark"]
    evaluation_config = config.get("evaluation", {})
    primary_split_seed = int(evaluation_config.get("primary_split_seed", config["random_seed"]))
    maximum_false_positive_rate = float(evaluation_config.get("maximum_false_positive_rate", 0.01))
    spec = BenchmarkSpec(
        clean_records=int(benchmark_config["clean_records"]),
        contributors=int(benchmark_config["contributors"]),
        entities=int(benchmark_config["entities"]),
        days=int(benchmark_config["days"]),
        max_contamination=float(benchmark_config["max_contamination"]),
        review_probability=float(benchmark_config["review_probability"]),
        random_seed=int(config["random_seed"]),
    )
    clean, attacks, catalog = generate_benchmark(entities, reviews, spec)
    clean.to_csv(processed / "benchmark_clean_control.csv", index=False, encoding="utf-8-sig")
    attacks.to_csv(processed / "benchmark_controlled_injections.csv", index=False, encoding="utf-8-sig")
    catalog.to_csv(processed / "benchmark_entity_catalog.csv", index=False, encoding="utf-8-sig")
    print(f"[OK] benchmark clean={len(clean):,} injected={len(attacks):,}")

    levels = [float(value) for value in benchmark_config["contamination_levels"]]
    split_source = subset_for_level(clean, attacks, max(levels))
    evaluation_split = balanced_group_split_map(split_source, random_state=primary_split_seed)
    tier_config = config["tiers"]
    thresholds = TierThresholds(
        trusted=float(tier_config["trusted"]),
        standard=float(tier_config["standard"]),
        watch=float(tier_config["watch"]),
        review_required=float(tier_config["review_required"]),
    )
    ranking_weights = {key: float(value) for key, value in config["scenarios"]["ranking_integrity"].items()}
    level_frames: dict[float, pd.DataFrame] = {}
    for level in levels:
        current = subset_for_level(clean, attacks, level)
        current["evaluation_split"] = current["record_id"].map(evaluation_split)
        if current["evaluation_split"].isna().any():
            raise RuntimeError("Evaluation split map is incomplete")
        features = extract_features(current)
        scored = score_records(
            features,
            ranking_weights,
            thresholds,
            minimum_weight=float(config["governance"]["minimum_weight"]),
        )
        level_frames[level] = scored
        print(f"[OK] features level={level:.0%} rows={len(scored):,}")

    training_frame = _build_training_frame(level_frames, levels, primary_split_seed)
    model = fit_risk_model(
        training_frame,
        random_state=primary_split_seed,
        maximum_false_positive_rate=maximum_false_positive_rate,
    )
    max_scored = level_frames[max(levels)]
    max_probability = model.predict_proba(max_scored)
    max_scored["risk_probability_model"] = max_probability
    max_scored["model_flag"] = max_probability >= model.threshold
    print(f"[OK] model validation threshold={model.threshold:.2f}")

    all_metrics: list[pd.DataFrame] = []
    ranking_rows: list[dict[str, Any]] = []
    for level in levels:
        scored = level_frames[level]
        methods, probability = evaluate_methods(scored, model)
        methods.insert(0, "contamination", level)
        all_metrics.append(methods)
        rank = ranking_metrics(clean, scored, probability, model.threshold)
        rank["contamination"] = level
        ranking_rows.append(rank)
        scored["risk_probability_model"] = probability
        print(f"[OK] evaluated level={level:.0%} rows={len(scored):,}")

    classification = pd.concat(all_metrics, ignore_index=True)
    ranking = pd.DataFrame(ranking_rows)
    headline = classification.merge(ranking, on="contamination", how="left")
    ablation = ablation_study(
        max_scored,
        random_state=primary_split_seed,
        maximum_false_positive_rate=maximum_false_positive_rate,
    )
    fairness = fairness_audit(max_scored, max_probability, model.threshold)
    sensitivity_seeds = [int(value) for value in evaluation_config.get("split_sensitivity_seeds", [primary_split_seed])]
    split_sensitivity, split_sensitivity_summary = _split_sensitivity_study(
        level_frames,
        levels,
        sensitivity_seeds,
        maximum_false_positive_rate,
    )
    classification.to_csv(output / "classification_metrics.csv", index=False)
    ranking.to_csv(output / "ranking_metrics.csv", index=False)
    ablation.to_csv(output / "ablation_metrics.csv", index=False)
    fairness.to_csv(output / "fairness_metrics.csv", index=False)
    split_sensitivity.to_csv(output / "split_sensitivity_metrics.csv", index=False)
    split_sensitivity_summary.to_csv(output / "split_sensitivity_summary.csv", index=False)
    headline.to_csv(output / "headline_metrics.csv", index=False)

    selected_columns = [
        "record_id", "entity_id", "contributor_id", "rating", "created_at", "attack_type",
        "ground_truth_risk", "P", "B", "C", "X", "T", "data_trust_score",
        "evidence_coverage", "uncertainty", "confidence", "tier", "recommended_action",
        "risk_probability_model", "model_flag",
    ]
    sample = (
        max_scored.sort_values("risk_probability_model", ascending=False)
        .head(5000)[selected_columns]
        .copy()
    )
    sample.to_csv(output / "scored_records_sample.csv", index=False, encoding="utf-8-sig")
    passports = sample.head(100).to_dict(orient="records")
    _write_json(output / "trust_passports.json", passports)

    audit = sample.head(500)[["record_id", "tier", "recommended_action", "risk_probability_model"]].copy()
    audit.insert(1, "event_type", "automated_risk_assessment")
    audit["decision_status"] = "pending_human_review"
    audit["event_time"] = started_at
    audit["model_version"] = config["version"]
    audit.to_csv(output / "audit_trail.csv", index=False, encoding="utf-8-sig")

    figures = _plot_results(output, headline, ablation, max_scored)
    proposed = classification.loc[classification["method"] == "multi_evidence_logistic"].copy()
    proposed_max = proposed.loc[proposed["contamination"].idxmax()].to_dict()
    rank_max = ranking.loc[ranking["contamination"].idxmax()].to_dict()
    dashboard = {
        "evidence_class": "E2_controlled_synthetic_benchmark_seeded_by_observed_distributions",
        "observed_data": json.loads((processed / "observed_data_summary.json").read_text(encoding="utf-8")),
        "benchmark": {
            "clean_records": len(clean),
            "maximum_injected_records": len(attacks),
            "attack_types": attacks["attack_type"].value_counts().to_dict(),
            "contamination_levels": levels,
            "metrics": proposed.merge(ranking, on="contamination", how="left")
            .rename(columns={"contamination": "contamination_level"})[
                [
                    "contamination_level",
                    "precision",
                    "recall",
                    "f1",
                    "auroc",
                    "auprc",
                    "fpr",
                    "raw_spearman",
                    "weighted_spearman",
                    "raw_topk_overlap",
                    "weighted_topk_overlap",
                    "raw_mean_rank_error",
                    "weighted_mean_rank_error",
                ]
            ]
            .to_dict(orient="records"),
        },
        "headline": {
            "risk_detection_f1_at_30pct": proposed_max.get("f1"),
            "risk_detection_auprc_at_30pct": proposed_max.get("auprc"),
            "false_positive_rate_at_30pct": proposed_max.get("fpr"),
            "raw_spearman_at_30pct": rank_max.get("raw_spearman"),
            "weighted_spearman_at_30pct": rank_max.get("weighted_spearman"),
            "ranking_spearman_improvement": (
                rank_max.get("weighted_spearman", 0) - rank_max.get("raw_spearman", 0)
            ),
            "validation_threshold": model.threshold,
        },
        "tier_distribution": max_scored["tier"].value_counts().to_dict(),
        "review_queue_count": int(max_scored["tier"].isin(["D_Review_Required", "E_Restricted"]).sum()),
        "passports": passports[:30],
        "fairness": fairness.to_dict(orient="records"),
        "split_sensitivity": split_sensitivity_summary.to_dict(orient="records"),
        "limitations": [
            "贡献者行为与时间戳来自受控合成基准；真实平台攻击模式需使用独立标注数据复核。",
            "已发表乐评摘录用于建立文本多样性基线；平台用户内容需另行开展专门标注。",
            "场景权重属于可解释的原型策略参数；真实平台试点阶段将依据标注与误报成本校准。",
        ],
    }
    _write_json(root / "app" / "data" / "dashboard.json", dashboard)
    _write_dashboard_script(root / "product" / "dashboard-data.js", dashboard)
    _write_json(output / "result_summary.json", dashboard)

    # The manifest lists digests for completed sibling outputs; its own digest is maintained externally.
    outputs = sorted(
        path
        for path in output.rglob("*")
        if path.is_file() and path.name != "run_manifest.json"
    )
    manifest = {
        "run_status": "success",
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": time.time() - started,
        "code_version": config["version"],
        "random_seed": config["random_seed"],
        "evidence_class": dashboard["evidence_class"],
        "inputs": {
            str(entity_path.relative_to(root)): _sha256(entity_path),
            str(review_path.relative_to(root)): _sha256(review_path),
            str(config_path.relative_to(root)): _sha256(config_path),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": {
                package: importlib.metadata.version(package)
                for package in ["numpy", "pandas", "scipy", "scikit-learn", "matplotlib", "PyYAML"]
            },
        },
        "outputs": {str(path.relative_to(root)): _sha256(path) for path in outputs},
        "figures": [str(path.relative_to(root)) for path in figures],
    }
    _write_json(output / "run_manifest.json", manifest)
    print(f"[OK] manifest={output / 'run_manifest.json'}")
    copied = _sync_evidence_mirror(root, output)
    print(f"[OK] evidence mirror artifacts={copied}")
    return dashboard
