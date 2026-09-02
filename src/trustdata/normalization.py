"""Stable identifiers and canonical names used by the final TrustData system."""

from __future__ import annotations

import hashlib
import re
import unicodedata

import pandas as pd


def stable_id(*parts: object, prefix: str = "id") -> str:
    joined = "\x1f".join("" if part is None else str(part) for part in parts)
    return f"{prefix}_{hashlib.sha256(joined.encode('utf-8')).hexdigest()[:20]}"


def normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", "" if pd.isna(value) else str(value))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "", text)
