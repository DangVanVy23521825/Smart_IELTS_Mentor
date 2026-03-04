"""
Orchestrate 2-phase RAG scoring for IELTS Writing Task 2.

Phase 1: Descriptor evidence → LLM (scoring_phase1.md) → TR/CC/LR/GRA + overall_band
Phase 2: Feedback + essay chunks evidence → LLM (coaching_phase2.md) → errors, improvements, study_plan
Merge → WritingAssessmentV1
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from app.schemas.assessment import (
    Citation,
    CriterionScore,
    ErrorItem,
    StudyPlanItem,
    WritingAssessmentV1,
)
from app.services.llm.openai_client import OpenAIClient
from app.services.rag.retriever import retrieve_citations

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from rag.retrieval.evidence import build_evidence_pack, citations_to_evidence_items, load_all_descriptors

logger = logging.getLogger(__name__)

DESCRIPTORS_JSONL = _PROJECT_ROOT / "data" / "processed" / "band_descriptors_task2.jsonl"
FILTER_PHASE2 = {"source_type": {"$in": ["feedback_card", "essay_chunk"]}}
TOP_K_PHASE2 = 8

LLM_MAX_RETRIES = 3


class ScoringError(Exception):
    """Raised when scoring pipeline fails (LLM timeout, parse error, etc)."""


def _load_prompt(name: str) -> str:
    path = _PROJECT_ROOT / "rag" / "prompts" / name
    return path.read_text(encoding="utf-8")


def _build_query_phase2(essay: str) -> str:
    return f"essay feedback improvements for: {essay[:500]}"


def _parse_phase1_response(
    obj: dict[str, Any],
    index_to_snippet: dict[int, str],
    index_to_band: dict[int, float],
) -> tuple[float, list[CriterionScore]]:
    """
    Parse LLM output from scoring_phase1.md → overall_band, criteria.
    Maps citation indices to snippets. Chỉ giữ citation khi band khớp; không match thì bỏ.
    """
    if "overall_band" not in obj:
        raise ValueError("LLM response missing 'overall_band'")
    overall = float(obj["overall_band"])
    if not 0 <= overall <= 9:
        raise ValueError(f"overall_band out of range: {overall}")

    criteria_raw = obj.get("criteria")
    if not isinstance(criteria_raw, dict):
        raise ValueError("LLM response missing or invalid 'criteria' (must be object)")

    criteria: list[CriterionScore] = []
    for key in ("TR", "CC", "LR", "GRA"):
        c = criteria_raw.get(key)
        if not isinstance(c, dict):
            raise ValueError(f"LLM response missing criterion '{key}'")
        band = c.get("band")
        justification = c.get("justification")
        if band is None:
            raise ValueError(f"Criterion '{key}' missing 'band'")
        if justification is None or not str(justification).strip():
            raise ValueError(f"Criterion '{key}' missing 'justification'")

        criterion_band = float(band)
        citations_raw = c.get("citations") or []
        citations: list[Citation] = []
        for idx in citations_raw:
            if not isinstance(idx, int):
                continue
            if idx not in index_to_snippet:
                continue
            cited_band = index_to_band.get(idx)
            if cited_band is not None and abs(cited_band - criterion_band) > 0.01:
                logger.warning(
                    "Citation mismatch: %s band %.1f cited descriptor band %.1f (index %d)",
                    key, criterion_band, cited_band, idx,
                )
                continue
            citations.append(
                Citation(
                    source_type="descriptor",
                    snippet=index_to_snippet[idx][:800],
                )
            )

        criteria.append(
            CriterionScore(
                criterion=key,
                band=float(band),
                justification=str(justification).strip(),
                citations=citations,
            )
        )
    return overall, criteria


def _parse_phase2_response(obj: dict[str, Any]) -> tuple[list[ErrorItem], list[str], list[StudyPlanItem]]:
    """
    Parse LLM output from coaching_phase2.md → errors, improvements, study_plan.
    Validates structure; missing optional fields get safe defaults.
    """
    errors_raw = obj.get("errors")
    if errors_raw is None:
        errors_raw = []
    if not isinstance(errors_raw, list):
        raise ValueError("LLM response 'errors' must be a list")

    errors: list[ErrorItem] = []
    for e in errors_raw:
        if isinstance(e, dict):
            msg = e.get("message")
            if msg is None or not str(msg).strip():
                logger.warning("Error item missing 'message', skipping")
                continue
            errors.append(
                ErrorItem(
                    type=e.get("type", "unknown"),
                    severity=e.get("severity", "medium"),
                    location=e.get("location"),
                    message=str(msg).strip(),
                    suggestion=e.get("suggestion", ""),
                    fixed_example=e.get("fixed_example"),
                )
            )
        elif isinstance(e, str) and e.strip():
            errors.append(
                ErrorItem(type="general", severity="medium", message=e.strip(), suggestion="")
            )

    improvements = obj.get("improvements")
    if improvements is None:
        improvements = []
    if not isinstance(improvements, list):
        improvements = []
    improvements = [str(x) for x in improvements if x is not None]

    study_plan_raw = obj.get("study_plan")
    if study_plan_raw is None:
        study_plan_raw = []
    if not isinstance(study_plan_raw, list):
        study_plan_raw = []
    study_plan: list[StudyPlanItem] = []
    for x in study_plan_raw:
        if isinstance(x, dict):
            focus = x.get("focus_area") or x.get("focus") or ""
            activities = x.get("activities") or []
            if isinstance(activities, list):
                activities = [str(a) for a in activities if a is not None]
            else:
                activities = []
            if focus:
                study_plan.append(StudyPlanItem(focus_area=str(focus), activities=activities))
        elif isinstance(x, str) and x.strip():
            study_plan.append(StudyPlanItem(focus_area=x.strip(), activities=[]))

    return errors, improvements, study_plan


def _validate_evidence_pack_no_leak(pack: Any) -> None:
    """
    Ensure Phase 1 and Phase 2 evidence are split correctly.
    Phase 1 should only contain descriptor content; Phase 2 only feedback/essay_chunk.
    """
    p1 = pack.phase1_descriptor
    p2 = pack.phase2_examples
    # Phase 1 block should mention descriptor, not feedback_card/essay_chunk in source line
    if "Source: feedback_card" in p1 or "Source: essay_chunk" in p1:
        logger.warning("Evidence leak: Phase 1 contains feedback_card or essay_chunk")
    if "Source: descriptor" in p2:
        logger.warning("Evidence leak: Phase 2 contains descriptor")


async def _call_llm_with_retry(
    client: OpenAIClient,
    system: str,
    user: str,
    parse_fn: Any,
    parse_kwargs: dict[str, Any] | None = None,
) -> Any:
    """
    Call LLM with retry. On parse failure, retry up to LLM_MAX_RETRIES.
    Raises ScoringError on final failure.
    """
    parse_kwargs = parse_kwargs or {}
    last_err: Exception | None = None

    for attempt in range(LLM_MAX_RETRIES):
        try:
            resp = await client.chat_json(
                system=system,
                user=user,
                temperature=0.2,
                max_output_tokens=1500,
                retries=1,
            )
            return parse_fn(resp.json_obj, **parse_kwargs)
        except (ValueError, KeyError, TypeError) as e:
            last_err = e
            logger.warning("LLM parse failed (attempt %d/%d): %s", attempt + 1, LLM_MAX_RETRIES, e)
            continue
        except Exception as e:
            last_err = e
            logger.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, LLM_MAX_RETRIES, e)
            continue

    raise ScoringError(f"Scoring pipeline failed after {LLM_MAX_RETRIES} retries") from last_err


async def assess_writing_task2(
    *,
    essay: str,
    prompt: str | None = None,
) -> WritingAssessmentV1:
    """
    Score Writing Task 2 via 2-phase RAG.

    - Phase 1: Descriptor evidence → band scoring (TR/CC/LR/GRA)
    - Phase 2: Feedback + essay chunks → coaching (errors, improvements, study_plan)

    Raises ScoringError on LLM timeout, JSON parse failure, or invalid format.
    """
    try:
        # Phase 1: Load tất cả descriptors từ JSONL (37 chunks)
        descriptors = load_all_descriptors(DESCRIPTORS_JSONL)
        # Retrieve Phase 2 (feedback + essay chunks only)
        query_phase2 = _build_query_phase2(essay)
        citations_phase2 = await retrieve_citations(
            query=query_phase2,
            top_k=TOP_K_PHASE2,
            metadata_filter=FILTER_PHASE2,
        )
        # Merge and build evidence pack (split by source_type)
        evidence_items = descriptors + citations_to_evidence_items(citations_phase2)
        pack = build_evidence_pack(evidence_items)

        _validate_evidence_pack_no_leak(pack)

        prompt_phase1_tpl = _load_prompt("scoring_phase1.md")
        prompt_phase2_tpl = _load_prompt("coaching_phase2.md")

        user_phase1 = prompt_phase1_tpl.replace("{{evidence}}", pack.phase1_descriptor).replace(
            "{{essay}}", essay
        )
        user_phase2 = prompt_phase2_tpl.replace("{{evidence}}", pack.phase2_examples).replace(
            "{{essay}}", essay
        )

        client = OpenAIClient()

        # Phase 1: Band scoring (with retry + validation)
        def _parse_phase1(obj: dict[str, Any]) -> tuple[float, list[CriterionScore]]:
            return _parse_phase1_response(
                obj, pack.phase1_index_to_snippet, pack.phase1_index_to_band
            )

        overall_band, criteria = await _call_llm_with_retry(
            client,
            system="You are an IELTS examiner. Return valid JSON only.",
            user=user_phase1,
            parse_fn=_parse_phase1,
        )

        # Phase 2: Coaching (with retry + validation)
        def _parse_phase2(obj: dict[str, Any]) -> tuple[list[ErrorItem], list[str], list[StudyPlanItem]]:
            return _parse_phase2_response(obj)

        errors, improvements, study_plan = await _call_llm_with_retry(
            client,
            system="You are an IELTS writing coach. Return valid JSON only.",
            user=user_phase2,
            parse_fn=_parse_phase2,
        )

        # Gộp improvements (string) thành StudyPlanItem nếu cần, lấy tối đa 3
        extra = [StudyPlanItem(focus_area=s, activities=[]) for s in improvements[:3 - len(study_plan)] if s.strip()]
        study_plan_final = (study_plan + extra)[:3]

        return WritingAssessmentV1(
            schema_version="v1",
            submission_type="writing",
            task="task2",
            overall_band=overall_band,
            criteria=criteria,
            errors=errors,
            study_plan=study_plan_final,
            improved_version=None,
            citations=[],
        )

    except ScoringError:
        raise
    except Exception as e:
        logger.exception("Scoring pipeline failed")
        raise ScoringError(f"Scoring failed: {e}") from e
