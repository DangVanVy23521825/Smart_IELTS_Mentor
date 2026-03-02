from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.schemas.assessment import Citation
from app.services.llm.openai_client import OpenAIClient
from app.services.rag.pinecone_client import PineconeRetriever


async def embed_text(text: str) -> list[float]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for embeddings")
    client = OpenAIClient()
    resp = await client._client.embeddings.create(  # type: ignore[attr-defined]
        model=settings.openai_embedding_model,
        input=text,
    )
    return list(resp.data[0].embedding)


async def retrieve_citations(
    *,
    query: str,
    top_k: int = 6,
    metadata_filter: dict[str, Any] | None = None,
) -> list[Citation]:
    if not settings.openai_api_key:
        return []
    retriever = PineconeRetriever()
    if not retriever.enabled:
        return []

    vector = await embed_text(query)
    matches = retriever.query(vector=vector, top_k=top_k, filter=metadata_filter)
    citations: list[Citation] = []
    for m in matches:
        md = m.get("metadata") or {}
        snippet = md.get("text") or md.get("snippet") or ""
        if not snippet:
            continue
        citations.append(
            Citation(
                source_type=md.get("source_type", "sample"),
                source_id=m.get("id"),
                title=md.get("title"),
                snippet=snippet[:800],
                criterion=md.get("criterion"),
                band=md.get("band"),
            )
        )
    return citations

