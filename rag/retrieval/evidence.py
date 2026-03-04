from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class EvidenceItem:
    """
    EvidenceItem is a class that represents a piece of evidence that supports a claim.
    """
    source_type: str
    criterion: str | None
    band: float | None
    snippet: str 
    source_id: str | None = None 
    
@dataclass
class EvidencePack:
    """
    EvidencePack is a class that represents a pack of evidence that supports a claim.
    phase1_index_to_snippet: map [1], [2], ... to actual snippet text for citation.
    phase1_index_to_band: map [1], [2], ... to band for citation validation.
    """
    phase1_descriptor: str
    phase2_examples: str
    phase1_index_to_snippet: Dict[int, str]
    phase1_index_to_band: Dict[int, float]
    stats: Dict[str, Any]

# ~37 descriptors × ~250 chars ≈ 9500; dùng 12000 để chứa hết
MAX_CHARS_PHASE1 = 12000
MAX_CHARS_PHASE2 = 4000


def build_evidence_pack(citations: List[EvidenceItem]) -> EvidencePack:
    """
    Split retrieved citations into:
    - Phase 1: Rubric / Descriptor evidence
    - Phase 2: Feedback / Example evidence
    """
    
    phase1_items = []
    phase2_items = []
    
    for c in citations:
        if c.source_type == "descriptor":
            phase1_items.append(c)
        else:
            phase2_items.append(c)
            
    phase1_text, phase1_index_to_snippet, phase1_index_to_band = format_evidence_block(
        phase1_items,
        title="IELTS Writing Task 2 band descriptors TR CC LR GRA",
        max_chars=MAX_CHARS_PHASE1,
    )
    phase2_text, _, _ = format_evidence_block(
        phase2_items,
        title="essay feedback improvements",
        max_chars=MAX_CHARS_PHASE2,
    )
    
    stats = {
        "phase1_count": len(phase1_items),
        "phase2_count": len(phase2_items),
        "total_count": len(citations),
    }
    
    return EvidencePack(
        phase1_descriptor=phase1_text,
        phase2_examples=phase2_text,
        phase1_index_to_snippet=phase1_index_to_snippet,
        phase1_index_to_band=phase1_index_to_band,
        stats=stats,
    )
    
def format_evidence_block(
    items: List[EvidenceItem],
    title: str,
    max_chars: int,
) -> tuple[str, Dict[int, str], Dict[int, float]]:
    """
    Format evidence items into a clean block for prompt usage.
    Deduplicate + truncate safely.
    Returns (formatted_text, index_to_snippet, index_to_band) for citation mapping & validation.
    """
    seen = set()
    blocks = []
    index_to_snippet: Dict[int, str] = {}
    index_to_band: Dict[int, float] = {}
    current_len = 0

    for i, item in enumerate(items, start=1):
        key = item.snippet.strip()
        if key in seen:
            continue
        seen.add(key)

        header = f"[{i}] Source: {item.source_type}"
        if item.criterion:
            header += f" | Criterion: {item.criterion}"
        if item.band is not None:
            header += f" | Band: {item.band}"

        block = f"{header}\n{item.snippet.strip()}\n"

        if current_len + len(block) > max_chars:
            break

        blocks.append(block)
        index_to_snippet[i] = item.snippet.strip()
        if item.band is not None:
            index_to_band[i] = float(item.band)
        current_len += len(block)

    if not blocks:
        return f"{title}:\n(No evidence retrieved)\n", {}, {}

    return f"{title}:\n" + "\n".join(blocks), index_to_snippet, index_to_band

def load_all_descriptors(jsonl_path: str | Path) -> List[EvidenceItem]:
    """
    Load tất cả descriptors từ JSONL (bỏ band 0 trống).
    Dùng cho Phase 1 thay vì retrieval - đảm bảo coverage đầy đủ.
    """
    path = Path(jsonl_path)
    items: List[EvidenceItem] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("source_type") != "descriptor":
                continue
            band = rec.get("band")
            if band is not None and float(band) == 0:
                continue
            text = rec.get("text") or ""
            if not text.strip():
                continue
            items.append(
                EvidenceItem(
                    source_type="descriptor",
                    criterion=rec.get("criterion"),
                    band=float(band) if band is not None else None,
                    snippet=text.strip()[:800],
                    source_id=rec.get("id"),
                )
            )
    return items


def citations_to_evidence_items(citations: List[Any]) -> List[EvidenceItem]:
    """
    Convert backend Citation schema to EvidenceItem.
    Keeps rag module decoupled from backend schema.
    """

    items: List[EvidenceItem] = []

    for c in citations:
        items.append(
            EvidenceItem(
                source_type=getattr(c, "source_type", "sample"),
                criterion=getattr(c, "criterion", None),
                band=getattr(c, "band", None),
                snippet=getattr(c, "snippet", ""),
                source_id=getattr(c, "source_id", None),
            )
        )

    return items