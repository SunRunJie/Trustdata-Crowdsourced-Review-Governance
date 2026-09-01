from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trustdata.benchmark import _choose_catalog
from trustdata.evaluation import _top_entity_ids, balanced_group_split_map, choose_threshold
from trustdata.features import extract_features
from trustdata.io import read_table, write_table
from trustdata.scoring import score_records


def sample_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "record_id": ["r1", "r2", "r3"],
            "entity_id": ["e1", "e1", "e2"],
            "contributor_id": ["u1", "u1", "u2"],
            "rating": [4.0, 5.0, 0.5],
            "review_text": ["A detailed original review", "A detailed original review", None],
            "created_at": ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z", "2026-01-02T00:00:00Z"],
            "source": ["platform", "platform", None],
            "version": ["v1", "v1", "v1"],
            "verification_level": ["platform_verified", "platform_verified", None],
            "ai_disclosure": ["unknown", "unknown", None],
            "account_age_days": [800, 800, 2],
            "entity_reference_score": [4.1, 4.1, 3.0],
            "cross_source_gap": [0.2, 0.2, 0.3],
        }
    )


def weights() -> dict[str, float]:
    return {
        "provenance": 0.10,
        "behavior": 0.30,
        "content": 0.10,
        "cross_source": 0.25,
        "temporal": 0.25,
    }


def test_feature_ranges_and_missing_content() -> None:
    result = extract_features(sample_frame())
    for field in ["provenance_risk", "behavior_risk", "cross_source_risk", "temporal_risk"]:
        assert result[field].between(0, 1).all()
    assert np.isnan(result.loc[2, "content_risk"])
    assert result.loc[2, "content_coverage"] == 0


def test_new_account_is_not_automatic_restriction() -> None:
    result = score_records(extract_features(sample_frame()), weights())
    assert result.loc[2, "new_account_signal"] > 0.9
    assert result.loc[2, "behavior_risk"] < 1.0


def test_duplicate_detection() -> None:
    result = extract_features(sample_frame())
    assert result.loc[0, "content_exact_group_size"] == 2
    assert result.loc[1, "content_exact_group_size"] == 2


def test_score_range_tiers_and_coverage() -> None:
    result = score_records(extract_features(sample_frame()), weights())
    assert result["data_trust_score"].between(0, 100).all()
    assert result["evidence_coverage"].between(0, 1).all()
    assert result["tier"].isin(
        ["A_Trusted", "B_Standard", "C_Watch", "D_Review_Required", "E_Restricted"]
    ).all()


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError):
        score_records(extract_features(sample_frame()), {"provenance": 0.5})


def test_csv_and_json_round_trip(tmp_path) -> None:
    frame = sample_frame()
    for suffix in (".csv", ".json", ".jsonl"):
        path = tmp_path / f"sample{suffix}"
        write_table(frame, path)
        loaded = read_table(path)
        assert len(loaded) == len(frame)


def test_threshold_respects_false_positive_constraint() -> None:
    truth = np.array([0] * 100 + [1] * 20)
    probability = np.array([0.05] * 98 + [0.75, 0.85] + [0.80] * 16 + [0.20] * 4)
    threshold = choose_threshold(truth, probability, maximum_false_positive_rate=0.01)
    prediction = probability >= threshold
    assert prediction[truth == 0].mean() <= 0.01


def test_group_split_is_complete_and_disjoint() -> None:
    rows = []
    for group_index in range(30):
        for record_index in range(3):
            rows.append(
                {
                    "record_id": f"r{group_index}_{record_index}",
                    "contributor_id": f"u{group_index}",
                    "ground_truth_risk": group_index % 2,
                }
            )
    frame = pd.DataFrame(rows)
    split_map = balanced_group_split_map(frame, random_state=101)
    assigned = frame.assign(split=frame["record_id"].map(split_map))
    assert assigned["split"].notna().all()
    assert set(assigned["split"]) == {"train", "validation", "test"}
    assert assigned.groupby("contributor_id")["split"].nunique().max() == 1
    shuffled = frame.sample(frac=1, random_state=7).reset_index(drop=True)
    assert balanced_group_split_map(shuffled, random_state=101) == split_map


def test_catalog_selection_is_independent_of_input_order() -> None:
    frame = pd.DataFrame(
        {
            "record_id": [f"r{index:03d}" for index in range(140)],
            "entity_id": [f"e{index:03d}" for index in range(140)],
            "rating_count": [(index % 7) + 1 for index in range(140)],
            "cross_source_reference": [4.0] * 140,
            "cross_source_gap": [0.1] * 140,
        }
    )
    expected = _choose_catalog(frame, 100)["record_id"].tolist()
    shuffled = frame.sample(frac=1, random_state=19).reset_index(drop=True)
    assert _choose_catalog(shuffled, 100)["record_id"].tolist() == expected


def test_top_entity_ties_use_entity_id_as_tiebreaker() -> None:
    frame = pd.DataFrame({"score": [1.0] * 105}, index=[f"e{index:03d}" for index in range(104, -1, -1)])
    assert _top_entity_ids(frame, "score", 100) == {f"e{index:03d}" for index in range(100)}


def test_csv_writer_uses_lf_on_all_platforms(tmp_path) -> None:
    path = tmp_path / "portable.csv"
    write_table(sample_frame(), path)
    payload = path.read_bytes()
    assert b"\r\n" not in payload
    assert payload.count(b"\n") == len(sample_frame()) + 1
