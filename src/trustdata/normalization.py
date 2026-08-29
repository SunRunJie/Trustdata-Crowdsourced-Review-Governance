"""Normalize the documented prior archives into TrustData input tables."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd


def stable_id(*parts: object, prefix: str = "id") -> str:
    joined = "\x1f".join("" if part is None else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(joined.encode('utf-8')).hexdigest()[:20]}"


def normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", "" if pd.isna(value) else str(value))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def numeric_count(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(r"[^0-9.-]", "", regex=True), errors="coerce"
    )


def _release_year(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.extract(r"(\d{4})", expand=False), errors="coerce")


def load_observed_entities(prior_root: Path) -> pd.DataFrame:
    external = prior_root / "data" / "external"
    frames: list[pd.DataFrame] = []

    history = pd.read_csv(external / "aoty_metacritic_30000" / "album_ratings.csv")
    history_frame = pd.DataFrame(
        {
            "platform": "AOTY_history",
            "artist": history["Artist"],
            "title": history["Title"],
            "release_year": pd.to_numeric(history["Release Year"], errors="coerce"),
            "rating": pd.to_numeric(history["AOTY User Score"], errors="coerce") / 20.0,
            "rating_count": pd.to_numeric(history["AOTY User Reviews"], errors="coerce"),
            "critic_rating": pd.to_numeric(history["AOTY Critic Score"], errors="coerce") / 20.0,
            "genres": history["Genre"],
            "snapshot_date": "2021-04-13",
            "source_dataset": "aoty_metacritic_30000",
            "source_license": "GPL-2.0",
        }
    )
    frames.append(history_frame)

    aoty = pd.read_csv(external / "aoty_top5000" / "aoty.csv")
    aoty_frame = pd.DataFrame(
        {
            "platform": "AOTY",
            "artist": aoty["artist"],
            "title": aoty["title"],
            "release_year": _release_year(aoty["release_date"]),
            "rating": pd.to_numeric(aoty["user_score"], errors="coerce") / 20.0,
            "rating_count": numeric_count(aoty["rating_count"]),
            "critic_rating": np.nan,
            "genres": aoty["genres"],
            "snapshot_date": "2024-10-20",
            "source_dataset": "aoty_top5000",
            "source_license": "CC-BY-3.0",
        }
    )
    frames.append(aoty_frame)

    rym = pd.read_csv(external / "rym_top5000" / "rym_clean1.csv")
    rym_frame = pd.DataFrame(
        {
            "platform": "RYM",
            "artist": rym["artist_name"],
            "title": rym["release_name"],
            "release_year": _release_year(rym["release_date"]),
            "rating": pd.to_numeric(rym["avg_rating"], errors="coerce"),
            "rating_count": pd.to_numeric(rym["rating_count"], errors="coerce"),
            "critic_rating": np.nan,
            "genres": rym["primary_genres"],
            "snapshot_date": "2022-03-11",
            "source_dataset": "rym_top5000",
            "source_license": "not_specified",
        }
    )
    frames.append(rym_frame)

    entities = pd.concat(frames, ignore_index=True)
    entities = entities.loc[entities["artist"].notna() & entities["title"].notna()].copy()
    entities["release_year"] = entities["release_year"].astype("Int64")
    entities["match_key"] = [
        f"{normalize_name(artist)}|{normalize_name(title)}|{'' if pd.isna(year) else int(year)}"
        for artist, title, year in zip(
            entities["artist"], entities["title"], entities["release_year"], strict=False
        )
    ]
    entities["entity_id"] = entities["match_key"].map(lambda value: stable_id(value, prefix="entity"))
    entities["record_id"] = [
        stable_id(platform, entity_id, snapshot, prefix="entity_record")
        for platform, entity_id, snapshot in zip(
            entities["platform"], entities["entity_id"], entities["snapshot_date"], strict=False
        )
    ]
    entities["entity_type"] = "music_album"
    entities["source"] = entities["source_dataset"]
    entities["verification_level"] = "third_party_observed_archive"
    entities["version"] = "prior_88e0ab65"
    entities["is_synthetic"] = False

    consensus = (
        entities.loc[entities["platform"].isin(["AOTY_history", "RYM"])]
        .drop_duplicates(["platform", "match_key"])
        .pivot(index="match_key", columns="platform", values="rating")
    )
    if {"AOTY_history", "RYM"}.issubset(consensus.columns):
        consensus["cross_source_gap"] = (consensus["AOTY_history"] - consensus["RYM"]).abs()
        consensus["cross_source_reference"] = consensus[["AOTY_history", "RYM"]].mean(axis=1)
        entities = entities.merge(
            consensus[["cross_source_gap", "cross_source_reference"]],
            left_on="match_key",
            right_index=True,
            how="left",
        )
    else:
        entities["cross_source_gap"] = np.nan
        entities["cross_source_reference"] = np.nan
    return entities


def load_observed_reviews(prior_root: Path) -> pd.DataFrame:
    review_dir = (
        prior_root
        / "data"
        / "external"
        / "aoty_metacritic_30000"
        / "Review excerpts for NLP"
    )
    frames: list[pd.DataFrame] = []
    for split in ("train", "test"):
        source = pd.read_csv(review_dir / f"{split}.csv")
        frame = pd.DataFrame(
            {
                "platform": "published_critic_archive",
                "artist": source["Artist"],
                "title": source["Title"],
                "contributor_source": source["Source"],
                "rating_raw": pd.to_numeric(source["Rating"], errors="coerce"),
                "review_text": source["Review"],
                "reception": source["Reception"],
                "archive_split": split,
            }
        )
        frames.append(frame)
    reviews = pd.concat(frames, ignore_index=True)
    reviews["review_text"] = reviews["review_text"].astype("string")
    reviews = reviews.loc[reviews["review_text"].notna() & reviews["review_text"].str.strip().ne("")].copy()
    reviews["entity_id"] = [
        stable_id(normalize_name(artist), normalize_name(title), prefix="review_entity")
        for artist, title in zip(reviews["artist"], reviews["title"], strict=False)
    ]
    reviews["contributor_id"] = reviews["contributor_source"].map(
        lambda value: stable_id(value, prefix="publication")
    )
    reviews["rating"] = (reviews["rating_raw"] / 20.0).clip(0, 5)
    reviews["record_id"] = [
        stable_id(split, index, entity, contributor, prefix="review")
        for index, (split, entity, contributor) in enumerate(
            zip(
                reviews["archive_split"],
                reviews["entity_id"],
                reviews["contributor_id"],
                strict=False,
            )
        )
    ]
    reviews["entity_type"] = "music_album"
    reviews["source"] = "aoty_metacritic_published_reviews"
    reviews["verification_level"] = "third_party_observed_archive"
    reviews["version"] = "prior_88e0ab65"
    reviews["ai_disclosure"] = "unknown"
    reviews["is_synthetic"] = False
    reviews["provenance_status"] = "observed_published_text"
    return reviews

