"""
Evaluate RAG runtime metrics:
- Latency (retrieval, phase1 LLM, phase2 LLM, total)
- Token usage per request (input/output/total)

Run from project root:
  python3 scripts/eval_rag_runtime.py --max-samples 20
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.services.llm.openai_client import OpenAIClient
from app.services.rag.retriever import retrieve_citations
from app.services.scoring.writing import (
    DESCRIPTORS_JSONL,
    FILTER_PHASE2,
    TOP_K_PHASE2,
    _build_query_phase2,
    _load_prompt,
    _parse_phase1_response,
    _parse_phase2_response,
)
from rag.retrieval.evidence import (
    build_evidence_pack,
    citations_to_evidence_items,
    load_all_descriptors,
)

from rag_eval_common import DATASET_DEFAULT, load_dataset_rows, usage_totals


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    s = sorted(values)
    idx = int(round((p / 100.0) * (len(s) - 1)))
    idx = max(0, min(idx, len(s) - 1))
    return s[idx]


async def _call_and_parse_with_retry(
    *,
    client: OpenAIClient,
    system: str,
    user: str,
    parse_fn: Callable[[dict[str, Any]], Any],
    retries: int,
    model: str | None,
) -> tuple[Any, float, int, int, int]:
    """
    Returns: (parsed_obj, latency_sec, input_tokens, output_tokens, total_tokens)
    """
    last_err: Exception | None = None
    total_latency = 0.0
    input_tok = 0
    output_tok = 0
    total_tok = 0

    for _ in range(retries + 1):
        t0 = time.perf_counter()
        try:
            resp = await client.chat_json(
                system=system,
                user=user,
                model=model,
                temperature=0.2,
                max_output_tokens=1500,
                retries=0,
            )
            elapsed = time.perf_counter() - t0
            total_latency += elapsed
            u_in, u_out, u_total = usage_totals(resp.usage)
            input_tok += u_in
            output_tok += u_out
            total_tok += u_total
            return parse_fn(resp.json_obj), total_latency, input_tok, output_tok, total_tok
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            total_latency += elapsed
            last_err = exc
            continue

    assert last_err is not None
    raise last_err


async def evaluate(max_samples: int | None, retries: int, model: str | None) -> int:
    rows = load_dataset_rows(DATASET_DEFAULT, max_samples=max_samples)
    if not rows:
        print("No essays found in dataset.")
        return 1

    descriptors = load_all_descriptors(DESCRIPTORS_JSONL)
    prompt_phase1_tpl = _load_prompt("scoring_phase1.md")
    prompt_phase2_tpl = _load_prompt("coaching_phase2.md")
    client = OpenAIClient()

    retrieval_latencies: list[float] = []
    phase1_latencies: list[float] = []
    phase2_latencies: list[float] = []
    total_latencies: list[float] = []
    req_input_tokens: list[int] = []
    req_output_tokens: list[int] = []
    req_total_tokens: list[int] = []
    failures = 0

    for i, row in enumerate(rows, start=1):
        essay = str(row["essay"])
        total_t0 = time.perf_counter()
        try:
            retr_t0 = time.perf_counter()
            query_phase2 = _build_query_phase2(essay)
            citations_phase2 = await retrieve_citations(
                query=query_phase2,
                top_k=TOP_K_PHASE2,
                metadata_filter=FILTER_PHASE2,
            )
            retr_elapsed = time.perf_counter() - retr_t0
            retrieval_latencies.append(retr_elapsed)

            evidence_items = descriptors + citations_to_evidence_items(citations_phase2)
            pack = build_evidence_pack(evidence_items)

            user_phase1 = prompt_phase1_tpl.replace("{{evidence}}", pack.phase1_descriptor).replace(
                "{{essay}}", essay
            )
            user_phase2 = prompt_phase2_tpl.replace("{{evidence}}", pack.phase2_examples).replace(
                "{{essay}}", essay
            )

            def parse_phase1(obj: dict[str, Any]):
                return _parse_phase1_response(
                    obj,
                    pack.phase1_index_to_snippet,
                    pack.phase1_index_to_band,
                )

            _, p1_latency, p1_in, p1_out, p1_total = await _call_and_parse_with_retry(
                client=client,
                system="You are an IELTS examiner. Return valid JSON only.",
                user=user_phase1,
                parse_fn=parse_phase1,
                retries=retries,
                model=model,
            )
            phase1_latencies.append(p1_latency)

            _, p2_latency, p2_in, p2_out, p2_total = await _call_and_parse_with_retry(
                client=client,
                system="You are an IELTS writing coach. Return valid JSON only.",
                user=user_phase2,
                parse_fn=_parse_phase2_response,
                retries=retries,
                model=model,
            )
            phase2_latencies.append(p2_latency)

            elapsed_total = time.perf_counter() - total_t0
            total_latencies.append(elapsed_total)

            req_input_tokens.append(p1_in + p2_in)
            req_output_tokens.append(p1_out + p2_out)
            req_total_tokens.append(p1_total + p2_total)

            print(
                f"[{i}/{len(rows)}] "
                f"latency_total={elapsed_total:.2f}s "
                f"retr={retr_elapsed:.2f}s p1={p1_latency:.2f}s p2={p2_latency:.2f}s "
                f"tokens={p1_total + p2_total}"
            )
        except Exception as exc:
            failures += 1
            print(f"[{i}/{len(rows)}] FAILED: {exc}")

    succeeded = len(total_latencies)
    if succeeded == 0:
        print("All requests failed.")
        return 1

    print("\n=== Runtime summary ===")
    print(f"Requests attempted            : {len(rows)}")
    print(f"Requests succeeded            : {succeeded}")
    print(f"Requests failed               : {failures}")
    print(f"Success rate                  : {(succeeded / len(rows)):.1%}")
    print(f"Avg retrieval latency         : {statistics.mean(retrieval_latencies):.3f}s")
    print(f"Avg phase1 LLM latency        : {statistics.mean(phase1_latencies):.3f}s")
    print(f"Avg phase2 LLM latency        : {statistics.mean(phase2_latencies):.3f}s")
    print(f"Avg total latency             : {statistics.mean(total_latencies):.3f}s")
    print(f"P50 total latency             : {_percentile(total_latencies, 50):.3f}s")
    print(f"P95 total latency             : {_percentile(total_latencies, 95):.3f}s")
    print(f"Avg input tokens/request      : {statistics.mean(req_input_tokens):.1f}")
    print(f"Avg output tokens/request     : {statistics.mean(req_output_tokens):.1f}")
    print(f"Avg total tokens/request      : {statistics.mean(req_total_tokens):.1f}")
    print(f"P95 total tokens/request      : {_percentile([float(x) for x in req_total_tokens], 95):.1f}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate RAG runtime and token usage")
    parser.add_argument(
        "--max-samples",
        type=int,
        default=20,
        help="Number of essays to evaluate (default: 20)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retry count per LLM phase on parse/call failure (default: 2)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override model for runtime eval (default: OPENAI_MODEL)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    max_samples = args.max_samples if args.max_samples and args.max_samples > 0 else None
    retries = max(0, int(args.retries))
    model = args.model.strip() if isinstance(args.model, str) and args.model.strip() else None
    return asyncio.run(evaluate(max_samples=max_samples, retries=retries, model=model))


if __name__ == "__main__":
    raise SystemExit(main())
