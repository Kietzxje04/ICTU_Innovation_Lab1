from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from nexusops_agent.contracts.case import CaseContext


class WorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    product: Literal["CORPORATE_OVERDRAFT", "WORKING_CAPITAL"]
    nodes: list[str] = Field(min_length=1)
    max_rework: int = Field(default=1, ge=0, le=1)


class WorkflowView(WorkflowCreate):
    status: Literal["DRAFT", "PUBLISHED"]
    definition_hash: str
    validation_errors: list[str]
    created_by: str
    created_at: datetime
    published_at: datetime | None = None


class SignatureValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    signature_present: bool | None = None
    certificate_valid: bool | None = None
    digest_matches: bool | None = None


class MockActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RoutePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: CaseContext
