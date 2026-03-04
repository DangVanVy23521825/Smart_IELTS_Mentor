# Kiểm tra retrieve_citations với filter Phase 1 & Phase 2
# + build_evidence_pack có split đúng không
# Chạy từ project root: python3 scripts/test_rag_retrieval.py
#
# Standalone: không dùng backend app, tránh lỗi import config
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from openai import AsyncOpenAI
from pinecone import Pinecone
from rag.retrieval.evidence import EvidenceItem, build_evidence_pack


async def embed_text(text: str) -> list[float]:
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = await client.embeddings.create(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        input=text,
    )
    return list(resp.data[0].embedding)


async def retrieve(
    query: str,
    top_k: int = 5,
    metadata_filter: dict | None = None,
) -> list[EvidenceItem]:
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pc.Index(os.getenv("PINECONE_INDEX_NAME"))
    vector = await embed_text(query)
    resp = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        namespace=os.getenv("PINECONE_NAMESPACE", "default"),
        filter=metadata_filter,
    )
    items = []
    for m in resp.matches or []:
        md = getattr(m, "metadata", None) or {}
        snippet = md.get("text") or md.get("snippet") or ""
        if not snippet:
            continue
        items.append(
            EvidenceItem(
                source_type=md.get("source_type", "sample"),
                criterion=md.get("criterion"),
                band=md.get("band"),
                snippet=snippet[:800],
                source_id=getattr(m, "id", None),
            )
        )
    return items


async def main():
    if not os.getenv("PINECONE_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Cần PINECONE_API_KEY và OPENAI_API_KEY trong .env")
        sys.exit(1)

    # Phase 1
    c1 = await retrieve(
        query="IELTS Writing Task 2 band descriptors TR CC LR GRA",
        top_k=5,
        metadata_filter={"source_type": {"$eq": "descriptor"}},
    )
    print("Phase 1 (descriptor):", len(c1), "citations")

    # Phase 2
    c2 = await retrieve(
        query="essay feedback improvements for: Some students prefer...",
        top_k=5,
        metadata_filter={"source_type": {"$in": ["feedback_card", "essay_chunk"]}},
    )
    print("Phase 2 (feedback/essay):", len(c2), "citations")

    all_items = c1 + c2
    pack = build_evidence_pack(all_items)
    print("Evidence pack stats:", pack.stats)
    print("Phase1 snippet count:", len(pack.phase1_index_to_snippet))
    print("OK - RAG retrieval hoạt động")


if __name__ == "__main__":
    asyncio.run(main())
