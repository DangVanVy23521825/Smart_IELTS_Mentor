from __future__ import annotations

from typing import Any

from app.core.config import settings


class PineconeRetriever:
    """
    Minimal wrapper so the rest of the code can run even when Pinecone isn't configured.
    """

    def __init__(self) -> None:
        self._enabled = bool(settings.pinecone_api_key and settings.pinecone_index_name)
        if self._enabled:
            from pinecone import Pinecone  # imported lazily

            pc = Pinecone(api_key=settings.pinecone_api_key)
            self._index = pc.Index(settings.pinecone_index_name)
        else:
            self._index = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    def query(self, *, vector: list[float], top_k: int, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not self._enabled or self._index is None:
            return []
        resp = self._index.query(
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            namespace=settings.pinecone_namespace,
            filter=filter,
        )
        matches = getattr(resp, "matches", None) or []
        out: list[dict[str, Any]] = []
        for m in matches:
            out.append(
                {
                    "id": getattr(m, "id", None),
                    "score": getattr(m, "score", None),
                    "metadata": getattr(m, "metadata", None) or {},
                }
            )
        return out

