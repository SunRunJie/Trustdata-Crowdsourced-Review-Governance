"""Run the TrustData pipeline from the repository root."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trustdata.pipeline import run_pipeline


if __name__ == "__main__":
    run_pipeline(ROOT, ROOT / "configs" / "trust.yaml")

