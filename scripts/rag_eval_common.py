"""
Common helpers for RAG evaluation scripts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATASET_DEFAULT = ROOT / "data" / "processed" / "task2_band7p5plus.jsonl"


def parse_gold_band(record: dict[str, Any]) -> float | None:
    value = record.get("band_value")
    if value is not None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    raw = record.get("band")
    if raw is None:
        return None
    token = str(raw).strip().split()
    if not token:
        return None
    try:
        return float(token[0])
    except ValueError:
        return None


def load_dataset_rows(dataset_path: Path, max_samples: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with dataset_path.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            essay = str(rec.get("essay") or "").strip()
            if not essay:
                continue
            rows.append(rec)
            if max_samples is not None and len(rows) >= max_samples:
                break
    return rows


def usage_totals(usage: dict[str, Any] | None) -> tuple[int, int, int]:
    """
    Normalize OpenAI usage payload across response formats.
    Returns: (input_tokens, output_tokens, total_tokens)
    """
    if not usage:
        return 0, 0, 0

    input_tokens = int(
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or usage.get("input_token_count")
        or 0
    )
    output_tokens = int(
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or usage.get("output_token_count")
        or 0
    )
    total_tokens = int(
        usage.get("total_tokens")
        or usage.get("token_count")
        or (input_tokens + output_tokens)
    )
    return input_tokens, output_tokens, total_tokens
