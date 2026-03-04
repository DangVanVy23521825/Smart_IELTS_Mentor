from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SchemaVersion = Literal["v1"]


class Citation(BaseModel):
    source_type: Literal["descriptor", "sample", "error_pattern", "feedback_card", "essay_chunk"]
    source_id: str | None = None
    title: str | None = None
    snippet: str
    criterion: Literal["TR", "CC", "LR", "GRA"] | None = None
    band: float | None = None


class ErrorItem(BaseModel):
    type: str = Field(description="taxonomy key, e.g. grammar:sv_agreement")
    severity: Literal["low", "medium", "high"]
    location: str | None = Field(default=None, description="paragraph/sentence reference")
    message: str
    suggestion: str
    fixed_example: str | None = None


class StudyPlanItem(BaseModel):
    focus_area: str = Field(description="e.g. Essay Structure, Cohesion")
    activities: list[str] = Field(default_factory=list, description="actionable steps")


class CriterionScore(BaseModel):
    criterion: Literal["TR", "CC", "LR", "GRA"]
    band: float = Field(ge=0, le=9)
    justification: str
    key_issues: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class WritingAssessmentV1(BaseModel):
    schema_version: SchemaVersion = "v1"
    submission_type: Literal["writing"]
    task: Literal["task2"] = "task2"

    overall_band: float = Field(ge=0, le=9)
    criteria: list[CriterionScore]
    errors: list[ErrorItem] = Field(default_factory=list)
    study_plan: list[StudyPlanItem] = Field(default_factory=list, description="top 3 focus areas with activities")
    improved_version: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class SpeakingAssessmentV1(BaseModel):
    schema_version: SchemaVersion = "v1"
    submission_type: Literal["speaking"]
    part: Literal["part1", "part2", "part3"] | None = None

    overall_band: float = Field(ge=0, le=9)
    criteria: list[CriterionScore]
    errors: list[ErrorItem] = Field(default_factory=list)
    study_plan: list[StudyPlanItem] = Field(default_factory=list)
    transcript: str | None = None
    citations: list[Citation] = Field(default_factory=list)

