from __future__ import annotations

import os
import json
import asyncio
from typing import List, Dict, Any

from pinecone import Pinecone
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve()
while not (BASE_DIR / ".env").exists() and BASE_DIR != BASE_DIR.parent:
    BASE_DIR = BASE_DIR.parent

load_dotenv(BASE_DIR / ".env")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL")

BATCH_SIZE = 50
SLEEP_BETWEEN_BATCH = 0.5

JSONL_FILES = [
    BASE_DIR / "data/processed/band_descriptors_task2.jsonl",
    BASE_DIR / "data/processed/task2_band7p5plus_essay_chunks.jsonl",
    BASE_DIR / "data/processed/task2_band7p5plus_feedback_cards.jsonl",
]

class EmbedAndUpsert:
    def __init__(self):
        if not all([PINECONE_API_KEY, PINECONE_INDEX_NAME, OPENAI_API_KEY]):
            raise ValueError("Missing required environment variables.")

        # Pinecone
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.pc.Index(PINECONE_INDEX_NAME)

        # OpenAI
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)

        self.batch_size = BATCH_SIZE
        self.sleep_between_batch = SLEEP_BETWEEN_BATCH

    def load_jsonl(self, path: str) -> List[Dict[str, Any]]:
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))
        return records

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        response = await self.client.embeddings.create(
            model=EMBED_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def build_metadata(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Metadata must match PineconeRetriever filter usage. Pinecone rejects null values."""
        raw = {
            "source_type": record.get("source_type"),
            "criterion": record.get("criterion"),
            "band": record.get("band"),
            "task": record.get("task"),
            "prompt": record.get("prompt"),
            "parent_id": record.get("parent_id"),
            "chunk_index": record.get("chunk_index"),
            "card_type": record.get("card_type"),
            "text": (record.get("text") or "")[:2000],
        }
        # Pinecone chỉ chấp nhận string, number, boolean, list[str] - không chấp nhận null
        return {k: v for k, v in raw.items() if v is not None}

    async def process_file(self, file_path: str):
        print(f"\nProcessing: {file_path}")
        records = self.load_jsonl(file_path)
        total = len(records)

        for i in range(0, total, self.batch_size):
            batch = records[i : i + self.batch_size]
            texts = [r["text"] for r in batch]

            embeddings = await self.embed_batch(texts)

            vectors = []
            for rec, emb in zip(batch, embeddings):
                vectors.append(
                    {
                        "id": rec["id"],
                        "values": emb,
                        "metadata": self.build_metadata(rec),
                    }
                )

            self.index.upsert(
                vectors=vectors,
                namespace=PINECONE_NAMESPACE,
            )

            print(f"Upserted {i + len(batch)}/{total}")
            await asyncio.sleep(self.sleep_between_batch)

    async def run(self):
        for file in JSONL_FILES:
            await self.process_file(file)

        print("\nAll files ingested successfully.")


async def main():
    pipeline = EmbedAndUpsert()
    await pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())