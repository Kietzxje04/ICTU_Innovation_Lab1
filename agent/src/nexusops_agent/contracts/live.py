from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LiveAgentNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    review_points: list[str] = Field(default_factory=list, max_length=12)
    confidence: float = Field(default=0.5, ge=0, le=1)


class LiveDocumentClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=800)
    recognized_documents: list[str] = Field(default_factory=list)
    unknown_documents: list[str] = Field(default_factory=list)


class LiveCriticReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Literal["PASS", "REVISE", "ESCALATE"]
    findings: list[str] = Field(default_factory=list, max_length=20)
    summary: str = Field(min_length=1, max_length=1200)
