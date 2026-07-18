from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from .agent_service import AgentService
from .exceptions import DomainError
from .models import AgentArtifactRecord, AssessmentRunRecord, CaseRecord, ProposedActionRecord
from .repositories import (
    ActionRepository,
    AssessmentRepository,
    CaseRepository,
    action_schema,
    case_context_from_record,
    input_hash,
    run_schema,
)
from .schemas import AgentView, Company, ExecutionRecord, ProposedAction, ResolutionPackage


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _agent_view(artifact: AgentArtifactRecord, display_name: str) -> AgentView:
    state = {
        "PASS": "done",
        "WARNING": "running",
        "REVIEW_REQUIRED": "required",
        "BLOCKED": "required",
    }[artifact.status]
    confidence = {"PASS": 95, "WARNING": 78, "REVIEW_REQUIRED": 65, "BLOCKED": 40}[artifact.status]
    result = artifact.warnings[0] if artifact.warnings else artifact.status
    return AgentView(name=display_name, state=state, confidence=confidence, result=result)


def company_projection(case: CaseRecord, run: AssessmentRunRecord | None = None) -> Company:
    artifacts = {artifact.agent_id: artifact for artifact in run.artifacts} if run and run.artifacts else {}
    views: list[AgentView] = []
    display_nodes = [
        ("CREDIT_AGENT", "Agent Tín dụng"),
        ("COMPLIANCE_AGENT", "Agent Tuân thủ"),
        ("TAX_CONSISTENCY", "Agent Thuế"),
        ("PRODUCT_AGENT", "Agent Sản phẩm"),
    ]
    for node_id, display_name in display_nodes:
        artifact = artifacts.get(node_id)
        if artifact:
            views.append(_agent_view(artifact, display_name))
        else:
            views.append(AgentView(name=display_name, state="optional", confidence=0, result="NOT_ROUTED"))

    warnings = _unique([warning for artifact in artifacts.values() for warning in artifact.warnings])
    agreements = [artifact.summary for artifact in artifacts.values() if artifact.status == "PASS"]
    proposed = _unique([action for artifact in artifacts.values() for action in artifact.proposed_actions])
    return Company(
        id=case.case_id,
        code=case.code,
        name=case.name,
        shortName=case.short_name,
        owner=case.owner,
        amount=case.display_amount,
        purpose=case.purpose,
        sla=case.sla,
        submitted=case.submitted_label,
        agent=case.agent_label,
        score=case.score,
        status=case.display_status,
        risk=case.risk,
        issue=case.issue,
        recommendation=proposed[0] if proposed else "RUN_AGENT_ASSESSMENT",
        consensus=agreements[:4],
        objections=warnings[:6],
        agents=views,
    )


class AssessmentService:
    def __init__(self, session: Session, agent_service: AgentService) -> None:
        self.session = session
        self.cases = CaseRepository(session)
        self.runs = AssessmentRepository(session)
        self.agent_service = agent_service

    def run(self, case_id: str, idempotency_key: str) -> AssessmentRunRecord:
        case = self.cases.get(case_id)
        if case is None:
            raise DomainError(404, "CASE_NOT_FOUND", "Case not found")
        existing = self.runs.get_by_idempotency(case_id, idempotency_key)
        if existing:
            return self.runs.get(existing.run_id) or existing
        context = case_context_from_record(case)
        record = self.runs.create(case_id, idempotency_key, context)
        try:
            state = self.agent_service.run(context)
            return self.runs.complete(record, state)
        except Exception as exc:
            self.runs.fail(record, exc)
            raise DomainError(502, "AGENT_RUN_FAILED", "Agent workflow failed", str(exc)) from exc

    def latest_or_run(self, case_id: str) -> AssessmentRunRecord:
        case = self.cases.get(case_id)
        if case is None:
            raise DomainError(404, "CASE_NOT_FOUND", "Case not found")
        context = case_context_from_record(case)
        current_hash = input_hash(context)
        latest = self.runs.latest(case_id)
        if latest and latest.input_hash == current_hash:
            return self.runs.get(latest.run_id) or latest
        return self.run(case_id, f"auto-{current_hash}")

    def get(self, case_id: str, run_id: str) -> AssessmentRunRecord:
        record = self.runs.get(run_id)
        if record is None or record.case_id != case_id:
            raise DomainError(404, "ASSESSMENT_RUN_NOT_FOUND", "Assessment run not found")
        return record


class ResolutionService:
    def __init__(self, session: Session, assessments: AssessmentService) -> None:
        self.session = session
        self.assessments = assessments
        self.cases = CaseRepository(session)
        self.actions = ActionRepository(session)

    def get(self, case_id: str, run_id: str | None = None) -> ResolutionPackage:
        case = self.cases.get(case_id)
        if case is None:
            raise DomainError(404, "CASE_NOT_FOUND", "Case not found")
        run = self.assessments.get(case_id, run_id) if run_id else self.assessments.latest_or_run(case_id)
        warnings = _unique([warning for artifact in run.artifacts for warning in artifact.warnings])
        outcome, action_type = self._outcome(run, warnings)
        action = self.actions.get_or_create(case, run, action_type)
        return ResolutionPackage(
            case=company_projection(case, run),
            run=run_schema(run),
            primary_outcome=outcome,
            blockers=warnings,
            routes=run.route,
            reason_codes=warnings or ["NO_UNRESOLVED_BLOCKER"],
            eligible_actions=[action_type],
            proposed_action=action_schema(action),
        )

    @staticmethod
    def _outcome(run: AssessmentRunRecord, warnings: list[str]) -> tuple[str, str]:
        if any("KYC" in item or "AML" in item for item in warnings):
            return "COMPLIANCE_REVIEW", "CREATE_COMPLIANCE_REVIEW_TASK"
        if "CIC_BAD_DEBT" in warnings or run.final_status == "BLOCKED":
            return "CREDIT_EXCEPTION_REVIEW", "CREATE_CREDIT_REVIEW_TASK"
        if any(item.startswith("MISSING_DOCUMENT") for item in warnings):
            return "DOCUMENT_REQUIRED", "REQUEST_MISSING_DOCUMENTS"
        if "FINANCIAL_TAX_MISMATCH" in warnings:
            return "TAX_RECONCILIATION_REQUIRED", "CREATE_TAX_RECONCILIATION_TASK"
        if run.final_status == "NEEDS_MORE_EVIDENCE":
            return "NEEDS_MORE_EVIDENCE", "CREATE_MANUAL_EVIDENCE_TASK"
        return "READY_FOR_HUMAN_REVIEW", "CREATE_DRAFT_REVIEW_PACKAGE"


class ActionService:
    APPROVER_ROLES = {"approver", "manager", "credit_officer"}

    def __init__(self, session: Session, resolution: ResolutionService) -> None:
        self.session = session
        self.resolution = resolution
        self.actions = ActionRepository(session)

    def list(self, case_id: str) -> list[ProposedAction]:
        package = self.resolution.get(case_id)
        return [package.proposed_action]

    def _load(self, case_id: str, action_id: str) -> ProposedActionRecord:
        record = self.actions.get(action_id)
        if record is None or record.case_id != case_id:
            raise DomainError(404, "ACTION_NOT_FOUND", "Action not found")
        return record

    @classmethod
    def require_role(cls, role: str) -> None:
        if role not in cls.APPROVER_ROLES:
            raise DomainError(403, "INSUFFICIENT_ROLE", "Approver role is required")

    def approve(
        self,
        case_id: str,
        action_id: str,
        approved_hash: str,
        user_id: str,
        role: str,
        idempotency_key: str,
        reason: str | None,
    ) -> ProposedAction:
        self.require_role(role)
        record = self._load(case_id, action_id)
        if record.status in {"APPROVED", "SUCCEEDED"}:
            return action_schema(record)
        if record.status == "REJECTED":
            raise DomainError(409, "ACTION_ALREADY_REJECTED", "Action was already rejected")
        if record.payload_hash != approved_hash:
            raise DomainError(409, "PAYLOAD_HASH_MISMATCH", "Action payload has changed")
        duplicate = self.session.query(ProposedActionRecord).filter_by(execution_idempotency_key=idempotency_key).first()
        if duplicate and duplicate.action_id != action_id:
            raise DomainError(409, "IDEMPOTENCY_KEY_REUSED", "Idempotency key belongs to another action")
        now = datetime.now(timezone.utc)
        record.status = "SUCCEEDED"
        record.approved_by = user_id
        record.decision_reason = reason
        record.decided_at = now
        record.external_ref = f"mock-{record.action_id}"
        record.execution_status = "SUCCEEDED"
        record.execution_idempotency_key = idempotency_key
        record.executed_at = now
        self.session.commit()
        return action_schema(record)

    def reject(self, case_id: str, action_id: str, user_id: str, role: str, reason: str) -> ProposedAction:
        self.require_role(role)
        record = self._load(case_id, action_id)
        if record.status == "REJECTED":
            return action_schema(record)
        if record.status in {"APPROVED", "SUCCEEDED"}:
            raise DomainError(409, "ACTION_ALREADY_EXECUTED", "Executed action cannot be rejected")
        record.status = "REJECTED"
        record.approved_by = user_id
        record.decision_reason = reason
        record.decided_at = datetime.now(timezone.utc)
        self.session.commit()
        return action_schema(record)

    def execution(self, case_id: str, action_id: str) -> ExecutionRecord:
        record = self._load(case_id, action_id)
        return ExecutionRecord(
            action_id=record.action_id,
            external_ref=record.external_ref,
            status=record.execution_status,
            idempotency_key=record.execution_idempotency_key,
            executed_at=record.executed_at,
        )
