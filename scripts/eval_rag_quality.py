"""
Evaluate RAG semantic quality:
- Faithfulness (criterion justification vs cited descriptor snippet)
- Context relevance (Phase-2 retrieved chunks vs essay)

Run from project root:
  python3 scripts/eval_rag_quality.py --max-samples 10 --judge-model gpt-4o-mini
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.services.llm.openai_client import OpenAIClient
from app.services.rag.retriever import retrieve_citations
from app.services.scoring.writing import FILTER_PHASE2, TOP_K_PHASE2
from app.services.scoring.writing import assess_writing_task2

from rag_eval_common import DATASET_DEFAULT, load_dataset_rows, usage_totals


def _build_phase2_query(essay: str) -> str:
    return f"essay feedback improvements for: {essay[:500]}"


def _build_faithfulness_prompt(criteria_payload: list[dict[str, str]]) -> str:
    payload = json.dumps(criteria_payload, ensure_ascii=False)
    return (
        "You are evaluating whether scoring justifications are faithful to cited IELTS descriptors.\n"
        "For each item, rate faithfulness from 1 to 5:\n"
        "- 5: fully supported by cited snippet\n"
        "- 4: mostly supported, minor extrapolation\n"
        "- 3: partly supported\n"
        "- 2: weakly supported\n"
        "- 1: unsupported or contradictory\n\n"
        "Return strict JSON only:\n"
        '{ "items": [{"criterion":"TR","score":1-5,"faithful":true/false,"reason":"..."}], "average_score": float }\n\n'
        f"Items:\n{payload}"
    )


def _build_context_relevance_prompt(essay: str, snippets: list[str]) -> str:
    compact = [{"index": i + 1, "snippet": s[:800]} for i, s in enumerate(snippets)]
    payload = json.dumps(compact, ensure_ascii=False)
    return (
        "You are evaluating retrieval relevance for IELTS Writing feedback.\n"
        "Given essay content and retrieved chunks, rate each chunk relevance from 1 to 5:\n"
        "- 5: directly useful for giving targeted feedback\n"
        "- 4: relevant and useful\n"
        "- 3: somewhat relevant\n"
        "- 2: weakly relevant\n"
        "- 1: irrelevant\n\n"
        "Return strict JSON only:\n"
        '{ "items":[{"index":1,"score":1-5,"reason":"..."}], "average_score": float }\n\n'
        f"Essay:\n{essay[:1400]}\n\nRetrieved chunks:\n{payload}"
    )


async def _judge_json_with_retry(
    *,
    client: OpenAIClient,
    system: str,
    user: str,
    model: str,
    retries: int,
) -> tuple[dict[str, Any], float, int, int, int]:
    last_err: Exception | None = None
    latency_total = 0.0
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
                temperature=0.0,
                max_output_tokens=1200,
                retries=0,
            )
            elapsed = time.perf_counter() - t0
            latency_total += elapsed
            u_in, u_out, u_total = usage_totals(resp.usage)
            input_tok += u_in
            output_tok += u_out
            total_tok += u_total
            return resp.json_obj, latency_total, input_tok, output_tok, total_tok
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            latency_total += elapsed
            last_err = exc
            continue

    assert last_err is not None
    raise last_err


async def evaluate(max_samples: int | None, top_k: int, judge_model: str, retries: int) -> int:
    rows = load_dataset_rows(DATASET_DEFAULT, max_samples=max_samples)
    if not rows:
        print("No essays found in dataset.")
        return 1

    judge_client = OpenAIClient()
    faithfulness_scores: list[float] = []
    faithfulness_binary: list[int] = []
    relevance_scores: list[float] = []
    relevance_high_ratio: list[float] = []
    judge_latencies: list[float] = []
    judge_total_tokens: list[int] = []
    criteria_without_citation = 0
    total_criteria = 0
    failures = 0

    for i, row in enumerate(rows, start=1):
        essay = str(row["essay"])
        prompt = row.get("prompt")
        try:
            assessment = await assess_writing_task2(essay=essay, prompt=prompt)

            crit_payload: list[dict[str, str]] = []
            for c in assessment.criteria:
                total_criteria += 1
                snippet = ""
                if c.citations:
                    snippet = c.citations[0].snippet
                else:
                    criteria_without_citation += 1
                crit_payload.append(
                    {
                        "criterion": c.criterion,
                        "band": f"{float(c.band):.1f}",
                        "justification": c.justification[:700],
                        "cited_snippet": snippet[:700],
                    }
                )

            faith_user = _build_faithfulness_prompt(crit_payload)
            faith_obj, faith_lat, _, _, faith_tok = await _judge_json_with_retry(
                client=judge_client,
                system="You are a strict evaluator. Return valid JSON only.",
                user=faith_user,
                model=judge_model,
                retries=retries,
            )
            judge_latencies.append(faith_lat)
            judge_total_tokens.append(faith_tok)

            faith_items = faith_obj.get("items") or []
            if isinstance(faith_items, list):
                scores = []
                faithful_flags = []
                for item in faith_items:
                    if not isinstance(item, dict):
                        continue
                    try:
                        score = float(item.get("score", 0))
                    except (TypeError, ValueError):
                        continue
                    if 1 <= score <= 5:
                        scores.append(score)
                        faithful_flags.append(1 if bool(item.get("faithful")) else 0)
                if scores:
                    faithfulness_scores.append(statistics.mean(scores))
                    faithfulness_binary.extend(faithful_flags)

            phase2_hits = await retrieve_citations(
                query=_build_phase2_query(essay),
                top_k=top_k,
                metadata_filter=FILTER_PHASE2,
            )
            snippets = [h.snippet for h in phase2_hits if (h.snippet or "").strip()]
            rel_user = _build_context_relevance_prompt(essay=essay, snippets=snippets)
            rel_obj, rel_lat, _, _, rel_tok = await _judge_json_with_retry(
                client=judge_client,
                system="You are a strict evaluator. Return valid JSON only.",
                user=rel_user,
                model=judge_model,
                retries=retries,
            )
            judge_latencies.append(rel_lat)
            judge_total_tokens.append(rel_tok)

            rel_items = rel_obj.get("items") or []
            if isinstance(rel_items, list):
                scores = []
                for item in rel_items:
                    if not isinstance(item, dict):
                        continue
                    try:
                        score = float(item.get("score", 0))
                    except (TypeError, ValueError):
                        continue
                    if 1 <= score <= 5:
                        scores.append(score)
                if scores:
                    relevance_scores.append(statistics.mean(scores))
                    relevance_high_ratio.append(sum(1 for s in scores if s >= 4.0) / len(scores))

            print(
                f"[{i}/{len(rows)}] "
                f"faith_avg={(faithfulness_scores[-1] if faithfulness_scores else 0):.2f} "
                f"relevance_avg={(relevance_scores[-1] if relevance_scores else 0):.2f}"
            )
        except Exception as exc:
            failures += 1
            print(f"[{i}/{len(rows)}] FAILED: {exc}")

    succeeded = len(rows) - failures
    if succeeded <= 0:
        print("All quality evaluations failed.")
        return 1

    print("\n=== Quality summary ===")
    print(f"Essays attempted                  : {len(rows)}")
    print(f"Essays succeeded                  : {succeeded}")
    print(f"Essays failed                     : {failures}")
    if faithfulness_scores:
        print(f"Faithfulness avg score (1-5)      : {statistics.mean(faithfulness_scores):.3f}")
    if faithfulness_binary:
        print(f"Faithfulness pass rate (judge)    : {(sum(faithfulness_binary) / len(faithfulness_binary)):.1%}")
    print(f"Criteria missing citation rate     : {(criteria_without_citation / max(1, total_criteria)):.1%}")
    if relevance_scores:
        print(f"Context relevance avg score (1-5) : {statistics.mean(relevance_scores):.3f}")
    if relevance_high_ratio:
        print(f"High relevance ratio (score>=4)    : {statistics.mean(relevance_high_ratio):.1%}")
    if judge_latencies:
        print(f"Avg judge latency/call            : {statistics.mean(judge_latencies):.3f}s")
    if judge_total_tokens:
        print(f"Avg judge tokens/call             : {statistics.mean(judge_total_tokens):.1f}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate faithfulness and context relevance")
    parser.add_argument(
        "--max-samples",
        type=int,
        default=10,
        help="Number of essays to evaluate (default: 10)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=8,
        help="Top-k chunks for relevance judge (default: 8)",
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default="gpt-4o-mini",
        help="Model used as LLM judge (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=1,
        help="Judge retry count per call (default: 1)",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    max_samples = args.max_samples if args.max_samples and args.max_samples > 0 else None
    top_k = max(1, int(args.top_k))
    retries = max(0, int(args.retries))
    judge_model = str(args.judge_model).strip() or "gpt-4o-mini"
    return asyncio.run(
        evaluate(
            max_samples=max_samples,
            top_k=top_k,
            judge_model=judge_model,
            retries=retries,
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
