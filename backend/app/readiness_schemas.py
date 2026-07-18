from __future__ import annotations

from typing import Any, Literal

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.evidence import CitationClaim, ValidationResult
from nexusops_agent.contracts.state import AgentArtifact
from pydantic import BaseModel, ConfigDict


class ReadinessTraceEvent(BaseModel):
    node: str
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "SKIPPED"]
    started_at: str | None = None
    duration_ms: float | None = None
    message: str


class EvidenceItem(BaseModel):
    chunk_id: str
    document_id: str
    document_number: str
    document_title: str
    domain: Literal["CASE_DATA", "AML", "LENDING", "DEMO_POLICY", "QUARANTINE"]
    source_type: Literal["CASE_RECORD", "INTERNAL_POLICY", "REGULATION", "DEMO_CONTENT"]
    source_authority: str
    validity_status: str
    effective_date: str
    article: str | None = None
    clause: str | None = None
    page_or_part: str | None = None
    citation_text: str
    full_content: str
    evaluation_basis: str
    content_hash: str
    quality_status: Literal["ACCEPTED", "REVIEW_REQUIRED", "DEMO_ONLY", "REJECTED"]
    validation: str
    reasons: list[str]
    related_nodes: list[str]
    case_field_refs: list[str]
    provenance: dict[str, str]


class ReadinessWorkflow(BaseModel):
    case: CaseContext
    route: list[str]
    artifacts: dict[str, AgentArtifact]
    citation_results: dict[str, ValidationResult]
    critic_verdict: Literal["PENDING", "PASS", "REVISE", "ESCALATE"]
    final_status: Literal["IN_PROGRESS", "READY_FOR_HUMAN_REVIEW", "NEEDS_MORE_EVIDENCE", "BLOCKED"]
    trace: list[ReadinessTraceEvent]


class ReadinessCase(BaseModel):
    id: str
    company_name: str
    owner: str
    submitted_at: str
    sla_due: str
    sla_target: str | None = None
    execution_duration_ms: float | None = None
    context: CaseContext
    workflow: ReadinessWorkflow
    evidence: list[EvidenceItem]


class CreateReadinessCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: CaseContext
    company_name: str
    owner: str
