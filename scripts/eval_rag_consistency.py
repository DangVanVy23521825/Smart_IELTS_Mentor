"""
Evaluate scoring consistency and output completeness.

Run from project root:
  python3 scripts/eval_rag_consistency.py --max-samples 5 --runs-per-essay 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.services.scoring.writing import assess_writing_task2

DATASET = ROOT / "data" / "processed" / "task2_band7p5plus.jsonl"
EXPECTED_CRITERIA = {"TR", "CC", "LR", "GRA"}


def _load_rows(max_samples: int | None) -> list[dict]:
    rows: list[dict] = []
    with DATASET.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("essay"):
                rows.append(rec)
            if max_samples is not None and len(rows) >= max_samples:
                break
    return rows


def _is_structurally_valid(result) -> bool:
    criteria = result.criteria or []
    criteria_names = {c.criterion for c in criteria}
    if criteria_names != EXPECTED_CRITERIA:
        return False
    if not (0 <= float(result.overall_band) <= 9):
        return False
    for c in criteria:
        if not (0 <= float(c.band) <= 9):
            return False
        if not c.justification or not c.justification.strip():
            return False
    if len(result.study_plan or []) > 3:
        return False
    return True


async def _run_once(essay: str, prompt: str | None):
    return await assess_writing_task2(essay=essay, prompt=prompt)


async def evaluate(max_samples: int | None, runs_per_essay: int) -> int:
    rows = _load_rows(max_samples=max_samples)
    if not rows:
        print("No essays to evaluate.")
        return 1

    per_essay_ranges: list[float] = []
    per_essay_stdevs: list[float] = []
    total_runs = 0
    successful_runs = 0
    valid_structure_runs = 0
    criteria_with_citations = 0
    total_criteria = 0

    for i, row in enumerate(rows, start=1):
        essay = str(row["essay"])
        prompt = row.get("prompt")
        bands: list[float] = []
        print(f"\nEssay {i}/{len(rows)}")
        for run in range(1, runs_per_essay + 1):
            total_runs += 1
            try:
                res = await _run_once(essay=essay, prompt=prompt)
                successful_runs += 1
                bands.append(float(res.overall_band))
                if _is_structurally_valid(res):
                    valid_structure_runs += 1

                for c in res.criteria:
                    total_criteria += 1
                    if c.citations:
                        criteria_with_citations += 1

                print(
                    f"  run={run} band={float(res.overall_band):.1f} "
                    f"criteria={[(c.criterion, float(c.band)) for c in res.criteria]}"
                )
            except Exception as exc:
                print(f"  run={run} FAILED: {exc}")

        if bands:
            band_range = max(bands) - min(bands)
            stdev = statistics.pstdev(bands) if len(bands) > 1 else 0.0
            per_essay_ranges.append(band_range)
            per_essay_stdevs.append(stdev)
            print(f"  range={band_range:.2f}, stdev={stdev:.3f}")

    print("\n=== Consistency summary ===")
    print(f"Essays evaluated               : {len(rows)}")
    print(f"Total runs                     : {total_runs}")
    print(f"Successful runs                : {successful_runs}")
    print(f"Run success rate               : {(successful_runs / total_runs):.1%}")
    print(f"Structure valid rate           : {(valid_structure_runs / max(1, successful_runs)):.1%}")
    print(
        f"Criteria citation coverage     : "
        f"{(criteria_with_citations / max(1, total_criteria)):.1%}"
    )
    if per_essay_ranges:
        print(f"Avg band range per essay       : {statistics.mean(per_essay_ranges):.3f}")
        print(f"Avg band stdev per essay       : {statistics.mean(per_essay_stdevs):.3f}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate RAG consistency/stability")
    parser.add_argument(
        "--max-samples",
        type=int,
        default=5,
        help="Number of essays to evaluate (default: 5)",
    )
    parser.add_argument(
        "--runs-per-essay",
        type=int,
        default=3,
        help="Repeated runs for each essay (default: 3)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    max_samples = args.max_samples if args.max_samples and args.max_samples > 0 else None
    runs = max(1, args.runs_per_essay)
    return asyncio.run(evaluate(max_samples=max_samples, runs_per_essay=runs))


if __name__ == "__main__":
    raise SystemExit(main())
