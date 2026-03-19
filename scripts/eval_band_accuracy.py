"""
Evaluate RAG band scoring accuracy quickly.

Run from project root:
  python3 scripts/eval_band_accuracy.py --max-samples 20
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.services.scoring.writing import assess_writing_task2

TEST_ESSAYS = ROOT / "data" / "processed" / "task2_band7p5plus.jsonl"


def _parse_gold_band(record: dict) -> float | None:
    value = record.get("band_value")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    raw = record.get("band")
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    token = text.split()[0]
    try:
        return float(token)
    except ValueError:
        return None


def _iter_dataset(max_samples: int | None) -> list[dict]:
    rows: list[dict] = []
    with TEST_ESSAYS.open("r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if not row.get("essay"):
                continue
            if _parse_gold_band(row) is None:
                continue
            rows.append(row)
            if max_samples is not None and len(rows) >= max_samples:
                break
    return rows


async def _score_essay(essay: str, prompt: str | None) -> float:
    result = await assess_writing_task2(essay=essay, prompt=prompt)
    return float(result.overall_band)


async def eval_accuracy(max_samples: int | None) -> int:
    rows = _iter_dataset(max_samples=max_samples)
    if not rows:
        print("No valid rows found in dataset.")
        return 1

    records: list[dict] = []
    failures = 0
    for idx, row in enumerate(rows, start=1):
        gold = _parse_gold_band(row)
        if gold is None:
            continue
        essay = str(row["essay"])
        prompt = row.get("prompt")
        try:
            pred = await _score_essay(essay=essay, prompt=prompt)
            err = abs(pred - gold)
            records.append(
                {
                    "idx": idx,
                    "gold": gold,
                    "pred": pred,
                    "abs_error": err,
                }
            )
            print(
                f"[{idx}/{len(rows)}] gold={gold:.1f} pred={pred:.1f} abs_err={err:.2f}"
            )
        except Exception as exc:
            failures += 1
            print(f"[{idx}/{len(rows)}] FAILED: {exc}")

    if not records:
        print("All samples failed to score.")
        return 1

    errors = [r["abs_error"] for r in records]
    mae = sum(errors) / len(errors)
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors))
    within_half = sum(1 for e in errors if e <= 0.5) / len(errors)
    within_one = sum(1 for e in errors if e <= 1.0) / len(errors)
    mean_pred = statistics.mean(r["pred"] for r in records)
    mean_gold = statistics.mean(r["gold"] for r in records)

    print("\n=== Accuracy summary ===")
    print(f"Samples attempted : {len(rows)}")
    print(f"Samples succeeded : {len(records)}")
    print(f"Samples failed    : {failures}")
    print(f"MAE               : {mae:.3f}")
    print(f"RMSE              : {rmse:.3f}")
    print(f"Within ±0.5       : {within_half:.1%}")
    print(f"Within ±1.0       : {within_one:.1%}")
    print(f"Mean gold band    : {mean_gold:.3f}")
    print(f"Mean pred band    : {mean_pred:.3f}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate RAG scoring band accuracy")
    parser.add_argument(
        "--max-samples",
        type=int,
        default=20,
        help="Number of essays to evaluate (default: 20)",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    max_samples = args.max_samples if args.max_samples and args.max_samples > 0 else None
    return asyncio.run(eval_accuracy(max_samples=max_samples))


if __name__ == "__main__":
    raise SystemExit(main())