"""Run the TrustData pipeline from the repository root."""

from __future__ import annotations

import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trustdata.pipeline import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the TrustData controlled benchmark.")
    parser.add_argument("--output", type=Path, default=None, help="Optional run-output directory")
    parser.add_argument("--processed", type=Path, default=None, help="Optional processed-data directory")
    parser.add_argument("--publish", action="store_true", help="Publish the final dashboard")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(ROOT, ROOT / "configs" / "trust.yaml", output_dir=args.output, processed_dir=args.processed,
                 publish=args.publish or args.output is None)

