from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaseRecord(Base):
    __tablename__ = "cases"

    case_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    short_name: Mapped[str] = mapped_column(String(160))
    owner: Mapped[str] = mapped_column(String(160))
    display_amount: Mapped[str] = mapped_column(String(80))
    purpose: Mapped[str] = mapped_column(String(255))
    sla: Mapped[str] = mapped_column(String(40))
    submitted_label: Mapped[str] = mapped_column(String(80))
    agent_label: Mapped[str] = mapped_column(String(80))
    score: Mapped[int] = mapped_column(Integer)
    display_status: Mapped[str] = mapped_column(String(80))
    risk: Mapped[str] = mapped_column(String(40))
    issue: Mapped[str] = mapped_column(Text)

    existing_customer: Mapped[bool] = mapped_column(Boolean)
    product: Mapped[str] = mapped_column(String(80))
    requested_amount: Mapped[float] = mapped_column(Float)
    relationship_months: Mapped[int] = mapped_column(Integer, default=0)
    submitted_documents: Mapped[list[str]] = mapped_column(JSON, default=list)
    required_documents: Mapped[list[str]] = mapped_column(JSON, default=list)
    annual_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    pretax_profit_last_2_years: Mapped[list[float]] = mapped_column(JSON, default=list)
    tax_declared_revenue: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_liabilities: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_cash_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    annual_debt_service: Mapped[float | None] = mapped_column(Float, nullable=True)
    collateral_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    twelve_month_account_turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    account_history_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    twelve_month_credit_turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_monthly_credit_inflow: Mapped[float | None] = mapped_column(Float, nullable=True)
    turnover_stability_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_utilization_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    negative_balance_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cleanup_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overdraft_purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loan_purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_conduct_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    cic_bad_debt: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    kyc_aml_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    case_metadata: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    runs: Mapped[list["AssessmentRunRecord"]] = relationship(back_populates="case")


class RoleRecord(Base):
    __tablename__ = "roles"

    role_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    approval_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)


class UserRecord(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(160))
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.role_id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuthSessionRecord(Base):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class LoanApprovalRecord(Base):
    __tablename__ = "loan_approvals"

    approval_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", index=True)
    current_role: Mapped[str] = mapped_column(String(40), default="EMPLOYEE")
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AssessmentRunRecord(Base):
    __tablename__ = "assessment_runs"
    __table_args__ = (UniqueConstraint("case_id", "idempotency_key", name="uq_run_case_idempotency"),)

    run_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(180))
    input_hash: Mapped[str] = mapped_column(String(64), index=True)
    workflow_id: Mapped[str] = mapped_column(String(120))
    workflow_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="PENDING")
    route: Mapped[list[str]] = mapped_column(JSON, default=list)
    critic_verdict: Mapped[str] = mapped_column(String(40), default="PENDING")
    final_status: Mapped[str] = mapped_column(String(60), default="IN_PROGRESS")
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped[CaseRecord] = relationship(back_populates="runs")
    artifacts: Mapped[list["AgentArtifactRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    citations: Mapped[list["CitationResultRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    events: Mapped[list["RunEventRecord"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class AgentArtifactRecord(Base):
    __tablename__ = "agent_artifacts"

    artifact_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("assessment_runs.run_id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(100), index=True)
    engine: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40))
    summary: Mapped[str] = mapped_column(Text)
    claims: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    metrics: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    proposed_actions: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    run: Mapped[AssessmentRunRecord] = relationship(back_populates="artifacts")


class CitationResultRecord(Base):
    __tablename__ = "citation_results"

    citation_result_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("assessment_runs.run_id"), index=True)
    claim_id: Mapped[str] = mapped_column(String(120), index=True)
    chunk_id: Mapped[str] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(60))
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)

    run: Mapped[AssessmentRunRecord] = relationship(back_populates="citations")


class RunEventRecord(Base):
    __tablename__ = "run_events"

    event_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("assessment_runs.run_id"), index=True)
    case_id: Mapped[str] = mapped_column(String(80), index=True)
    node_id: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(40))
    engine: Mapped[str] = mapped_column(String(120))
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    run: Mapped[AssessmentRunRecord] = relationship(back_populates="events")


class ProposedActionRecord(Base):
    __tablename__ = "proposed_actions"

    action_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.case_id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("assessment_runs.run_id"), index=True)
    action_type: Mapped[str] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING_APPROVAL")
    created_by: Mapped[str] = mapped_column(String(120), default="nexusops-agent")
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(160), nullable=True)
    execution_status: Mapped[str] = mapped_column(String(60), default="NOT_STARTED")
    execution_idempotency_key: Mapped[str | None] = mapped_column(String(180), nullable=True, unique=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowTemplateRecord(Base):
    __tablename__ = "workflow_templates"
    __table_args__ = (UniqueConstraint("workflow_id", "version", name="uq_workflow_version"),)

    record_id: Mapped[str] = mapped_column(String(180), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(String(120), index=True)
    version: Mapped[str] = mapped_column(String(40))
    product: Mapped[str] = mapped_column(String(80), index=True)
    nodes: Mapped[list[str]] = mapped_column(JSON, default=list)
    max_rework: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", index=True)
    definition_hash: Mapped[str] = mapped_column(String(64), index=True)
    validation_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_by: Mapped[str] = mapped_column(String(120), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EvaluationRunRecord(Base):
    __tablename__ = "evaluation_runs"

    run_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(40), default="COMPLETED")
    scenario_count: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MockExternalActionRecord(Base):
    __tablename__ = "mock_external_actions"

    external_ref: Mapped[str] = mapped_column(String(160), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    action_type: Mapped[str] = mapped_column(String(120), index=True)
    case_id: Mapped[str] = mapped_column(String(80), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="SUCCEEDED")
    approved_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
