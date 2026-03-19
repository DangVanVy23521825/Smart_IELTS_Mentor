"""
Evaluate Phase-2 retrieval hygiene (quick, no LLM judge).

Run from project root:
  python3 scripts/eval_rag_retrieval.py --max-samples 20 --top-k 8
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

from app.services.rag.retriever import retrieve_citations

DATASET = ROOT / "data" / "processed" / "task2_band7p5plus.jsonl"
ALLOWED_TYPES = {"feedback_card", "essay_chunk"}


def _load_essays(max_samples: int | None) -> list[str]:
    essays: list[str] = []
    with DATASET.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            essay = str(rec.get("essay") or "").strip()
            if essay:
                essays.append(essay)
            if max_samples is not None and len(essays) >= max_samples:
                break
    return essays


def _build_query_phase2(essay: str) -> str:
    return f"essay feedback improvements for: {essay[:500]}"


async def evaluate(max_samples: int | None, top_k: int) -> int:
    essays = _load_essays(max_samples=max_samples)
    if not essays:
        print("No essays found for retrieval evaluation.")
        return 1

    total_queries = 0
    successful_queries = 0
    total_hits = 0
    hit_rates: list[float] = []
    type_valid_hits = 0
    non_empty_snippets = 0
    unique_hit_rates: list[float] = []

    for i, essay in enumerate(essays, start=1):
        query = _build_query_phase2(essay)
        total_queries += 1
        try:
            hits = await retrieve_citations(
                query=query,
                top_k=top_k,
                metadata_filter={"source_type": {"$in": sorted(ALLOWED_TYPES)}},
            )
            successful_queries += 1
            count = len(hits)
            total_hits += count
            hit_rates.append(count / top_k if top_k > 0 else 0.0)

            unique_keys = set()
            for h in hits:
                if h.source_type in ALLOWED_TYPES:
                    type_valid_hits += 1
                snippet = (h.snippet or "").strip()
                if snippet:
                    non_empty_snippets += 1
                unique_keys.add((h.source_id, snippet[:120]))
            unique_hit_rates.append(len(unique_keys) / max(1, count))

            print(
                f"[{i}/{len(essays)}] hits={count}/{top_k} "
                f"unique={len(unique_keys)}/{max(1, count)}"
            )
        except Exception as exc:
            print(f"[{i}/{len(essays)}] FAILED: {exc}")

    if successful_queries == 0:
        print("All retrieval queries failed.")
        return 1

    print("\n=== Retrieval summary (Phase 2) ===")
    print(f"Queries attempted             : {total_queries}")
    print(f"Queries succeeded             : {successful_queries}")
    print(f"Query success rate            : {(successful_queries / total_queries):.1%}")
    print(f"Avg hits per query            : {(total_hits / successful_queries):.2f}")
    print(f"Avg hit-rate (hits/top_k)     : {statistics.mean(hit_rates):.1%}")
    print(f"Source-type compliance        : {(type_valid_hits / max(1, total_hits)):.1%}")
    print(f"Non-empty snippet rate        : {(non_empty_snippets / max(1, total_hits)):.1%}")
    print(f"Avg unique-hit rate           : {statistics.mean(unique_hit_rates):.1%}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Phase-2 retrieval hygiene")
    parser.add_argument(
        "--max-samples",
        type=int,
        default=20,
        help="Number of essays to evaluate (default: 20)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Retrieval top_k for each query (default: 8)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    max_samples = args.max_samples if args.max_samples and args.max_samples > 0 else None
    top_k = max(1, args.top_k)
    return asyncio.run(evaluate(max_samples=max_samples, top_k=top_k))


if __name__ == "__main__":
    raise SystemExit(main())
