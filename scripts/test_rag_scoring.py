# End-to-end scoring: Retrieve → Evidence pack → LLM Phase 1 → LLM Phase 2 → Merge
# Chạy từ project root: python3 scripts/test_rag_scoring.py
#
# Standalone: không dùng backend app, tránh lỗi import config
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT))

from openai import AsyncOpenAI
from pinecone import Pinecone
from rag.retrieval.evidence import EvidenceItem, build_evidence_pack, load_all_descriptors

# --- Config ---
DESCRIPTORS_JSONL = ROOT / "data" / "processed" / "band_descriptors_task2.jsonl"
FILTER_PHASE2 = {"source_type": {"$in": ["feedback_card", "essay_chunk"]}}
TOP_K_PHASE2 = 8
LLM_MAX_RETRIES = 3

SAMPLE_ESSAY = """
While some people maintain that the scarcity and high value of urban land make the preservation of old buildings impractical, others argue that such structures embody historical and cultural significance that warrants protection. This essay will examine both viewpoints before explaining why I believe conserving old buildings remains essential.

Those who support the demolition of old buildings tend to emphasize economic efficiency. In densely populated cities, where space is limited and demand for housing and commercial facilities is high, replacing outdated structures with modern developments can significantly optimize land use. Such projects often lead to higher property values, increased investment, and greater economic returns. Moreover, newly constructed buildings can be designed to incorporate cutting-edge technology and environmentally sustainable features, making them better suited to meet contemporary urban and ecological demands. From this perspective, preserving old buildings is viewed as a constraint on modernization and economic progress.

Despite these arguments, I strongly believe that old buildings play a vital role in preserving a city’s cultural identity. These structures act as tangible connections to the past, showcasing traditional architectural styles, craftsmanship, and social values that would otherwise be lost. Hoi An Ancient Town, for example, illustrates how well-preserved historic buildings can maintain a sense of continuity between past and present. Beyond their cultural value, such sites enhance the distinct character of cities, attract tourists, and foster a sense of pride and belonging among local communities.

In conclusion, although economic considerations lead some to advocate for the removal of old buildings, others recognize their irreplaceable cultural importance. While integrating historic structures into modern urban planning poses challenges, I firmly believe that they should be protected and thoughtfully incorporated into city development to ensure that our shared heritage is preserved for future generations.
"""


def _load_prompt(name: str) -> str:
    path = ROOT / "rag" / "prompts" / name
    return path.read_text(encoding="utf-8")


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


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


async def call_llm(
    client: AsyncOpenAI,
    system: str,
    user: str,
    model: str = "gpt-4o",
) -> dict[str, Any]:
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        max_tokens=1500,
    )
    text = resp.choices[0].message.content or ""
    return _extract_json(text)


def parse_phase1(
    obj: dict,
    index_to_snippet: dict[int, str],
    index_to_band: dict[int, float],
) -> tuple[float, list[dict]]:
    if "overall_band" not in obj:
        raise ValueError("LLM response missing 'overall_band'")
    overall = float(obj["overall_band"])
    criteria_raw = obj.get("criteria") or {}
    if not isinstance(criteria_raw, dict):
        raise ValueError("LLM response missing or invalid 'criteria'")
    criteria = []
    for key in ("TR", "CC", "LR", "GRA"):
        c = criteria_raw.get(key)
        if not isinstance(c, dict):
            raise ValueError(f"LLM response missing criterion '{key}'")
        band = c.get("band")
        justification = c.get("justification") or ""
        criterion_band = float(band) if band is not None else 0
        citations = []
        for i in (c.get("citations") or []):
            if not isinstance(i, int):
                continue
            if i not in index_to_snippet:
                continue
            cited_band = index_to_band.get(i)
            if cited_band is not None and abs(cited_band - criterion_band) > 0.01:
                continue  # Mismatch: bỏ, không thêm gì
            citations.append(index_to_snippet[i][:800])
        criteria.append({"criterion": key, "band": criterion_band, "justification": justification, "citations": citations})
    return overall, criteria


def parse_phase2(obj: dict) -> tuple[list[dict], list[str], list[dict]]:
    errors = [e if isinstance(e, dict) else {"message": str(e)} for e in (obj.get("errors") or [])]
    improvements = [str(x) for x in (obj.get("improvements") or []) if x is not None]
    study_plan_raw = obj.get("study_plan") or []
    study_plan = []
    for x in study_plan_raw:
        if isinstance(x, dict):
            focus = x.get("focus_area") or x.get("focus") or ""
            activities = x.get("activities") or []
            if isinstance(activities, list):
                activities = [str(a) for a in activities if a is not None]
            else:
                activities = []
            if focus:
                study_plan.append({"focus_area": str(focus), "activities": activities})
        elif isinstance(x, str) and x.strip():
            study_plan.append({"focus_area": x.strip(), "activities": []})
    return errors, improvements, study_plan


async def assess_writing(essay: str) -> dict[str, Any]:
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Phase 1: Load tất cả 37 descriptors từ JSONL (không dùng retrieval)
    descriptors = load_all_descriptors(DESCRIPTORS_JSONL)
    query_phase2 = f"essay feedback improvements for: {essay[:500]}"
    c2 = await retrieve(query_phase2, top_k=TOP_K_PHASE2, metadata_filter=FILTER_PHASE2)
    pack = build_evidence_pack(descriptors + c2)

    # Build prompts
    tpl1 = _load_prompt("scoring_phase1.md")
    tpl2 = _load_prompt("coaching_phase2.md")
    user1 = tpl1.replace("{{evidence}}", pack.phase1_descriptor).replace("{{essay}}", essay)
    user2 = tpl2.replace("{{evidence}}", pack.phase2_examples).replace("{{essay}}", essay)

    # Phase 1
    last_err = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            obj1 = await call_llm(client, "You are an IELTS examiner. Return valid JSON only.", user1, model)
            overall_band, criteria = parse_phase1(
                obj1, pack.phase1_index_to_snippet, pack.phase1_index_to_band
            )
            break
        except Exception as e:
            last_err = e
            print(f"  Phase 1 attempt {attempt + 1}/{LLM_MAX_RETRIES} failed: {e}")
    else:
        raise RuntimeError(f"Phase 1 failed after {LLM_MAX_RETRIES} retries") from last_err

    # Phase 2
    last_err = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            obj2 = await call_llm(client, "You are an IELTS writing coach. Return valid JSON only.", user2, model)
            errors, improvements, study_plan = parse_phase2(obj2)
            break
        except Exception as e:
            last_err = e
            print(f"  Phase 2 attempt {attempt + 1}/{LLM_MAX_RETRIES} failed: {e}")
    else:
        raise RuntimeError(f"Phase 2 failed after {LLM_MAX_RETRIES} retries") from last_err

    extra = [{"focus_area": s, "activities": []} for s in improvements[: max(0, 3 - len(study_plan))] if s.strip()]
    study_plan_final = (study_plan + extra)[:3]

    return {
        "schema_version": "v1",
        "submission_type": "writing",
        "task": "task2",
        "overall_band": overall_band,
        "criteria": criteria,
        "errors": errors,
        "study_plan": study_plan_final,
        "improved_version": None,
    }


async def main():
    if not os.getenv("PINECONE_API_KEY") or not os.getenv("OPENAI_API_KEY"):
        print("ERROR: Cần PINECONE_API_KEY và OPENAI_API_KEY trong .env")
        sys.exit(1)

    print("Running end-to-end scoring...")
    print("Essay:", SAMPLE_ESSAY[:100].strip(), "...")
    print()

    try:
        result = await assess_writing(SAMPLE_ESSAY)
        print("SUCCESS - RAG scoring hoạt động")
        print()
        print("overall_band:", result["overall_band"])
        print("criteria:", [(c["criterion"], c["band"]) for c in result["criteria"]])
        print("errors count:", len(result["errors"]))
        print("study_plan:", result["study_plan"])
        print()
        print("Full JSON:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print("FAILED:", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
