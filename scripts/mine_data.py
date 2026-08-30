"""Mine cross-source review data using LLM-driven web crawling.

Usage examples:

  # YAML task file
  python scripts/mine_data.py --task tasks/movies.yaml --output data/mined/movies.csv

  # Natural language task description
  python scripts/mine_data.py \
    --task "查找豆瓣和IMDB上关于盗梦空间的用户评分" \
    --output data/mined/movies.csv

  # Custom config + verbose logging
  python scripts/mine_data.py \
    --task tasks/restaurants.yaml \
    --output data/mined/restaurants.csv \
    --config configs/llm_mining_local.yaml \
    --verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trustdata.env import load_env_file
from trustdata.llm_mining import run_mining


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mine cross-source review data using LLM-driven web crawling."
    )
    parser.add_argument(
        "--task",
        required=True,
        help="Path to a YAML task file or a natural-language task description string.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output path for mined data (CSV/JSON/JSONL).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "llm_mining.yaml",
        help="LLM mining YAML config (default: configs/llm_mining.yaml).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(ROOT / ".env")

    # Determine whether --task is a file path or natural-language string
    task_path = Path(args.task)
    if task_path.suffix in (".yaml", ".yml") and task_path.exists():
        task_source: Path | str = task_path
    else:
        task_source = args.task

    df = run_mining(
        config_path=args.config,
        task_source=task_source,
        output_path=args.output,
        verbose=args.verbose,
    )

    print(f"[OK] mined records={len(df):,}")
    print(f"[OK] output={args.output}")
    summary_path = args.output.with_name(f"{args.output.stem}.mining_summary.json")
    if summary_path.exists():
        print(f"[OK] summary={summary_path}")
    unavailable_path = args.output.with_name(f"{args.output.stem}.source_unavailable.json")
    if unavailable_path.exists():
        print(f"[WARN] source unavailable report={unavailable_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
