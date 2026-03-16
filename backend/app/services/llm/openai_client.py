from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings


@dataclass(frozen=True)
class LLMResponse:
    json_obj: dict[str, Any]
    usage: dict[str, Any] | None


class OpenAIClient:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)

    async def chat_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1200,
        retries: int = 2,
    ) -> LLMResponse:
        model = model or settings.openai_model

        last_err: Exception | None = None
        for _ in range(retries + 1):
            try:
                resp = await asyncio.wait_for(
                    self._client.responses.create(
                        model=model,
                        input=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    ),
                    timeout=settings.openai_timeout_seconds + 5,
                )
                text = resp.output_text
                obj = _extract_json_object(text)
                usage = None
                if getattr(resp, "usage", None) is not None:
                    usage = resp.usage.model_dump()  # type: ignore[attr-defined]
                return LLMResponse(json_obj=obj, usage=usage)
            except Exception as e:
                last_err = e
                continue
        assert last_err is not None
        raise last_err


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        # strip fenced code blocks
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object")
        return parsed
    except json.JSONDecodeError:
        # best-effort: locate outermost {...}
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
        if not isinstance(parsed, dict):
            raise ValueError("Expected JSON object")
        return parsed

