from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.enums import ProductType
from nexusops_agent.contracts.state import WorkflowState
from nexusops_agent.nodes.readiness_rules import ReadinessRuleEngine
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .models import (
    AgentArtifactRecord,
    AssessmentRunRecord,
    CaseRecord,
    CitationResultRecord,
    ProposedActionRecord,
    RunEventRecord,
)
from .schemas import AssessmentRun, Company, ProposedAction


def case_context_from_record(record: CaseRecord) -> CaseContext:
    context = CaseContext(
        case_id=record.case_id,
        customer_id=record.customer_id,
        existing_customer=record.existing_customer,
        product=ProductType(record.product),
        requested_amount=record.requested_amount,
        relationship_months=record.relationship_months,
        submitted_documents=record.submitted_documents or [],
        required_documents=record.required_documents or [],
        annual_revenue=record.annual_revenue,
        pretax_profit_last_2_years=record.pretax_profit_last_2_years,
        tax_declared_revenue=record.tax_declared_revenue,
        current_assets=record.current_assets,
        current_liabilities=record.current_liabilities,
        total_debt=record.total_debt,
        total_assets=record.total_assets,
        operating_cash_flow=record.operating_cash_flow,
        annual_debt_service=record.annual_debt_service,
        collateral_ratio=record.collateral_ratio,
        twelve_month_account_turnover=record.twelve_month_account_turnover,
        account_history_months=record.account_history_months,
        twelve_month_credit_turnover=record.twelve_month_credit_turnover,
        average_monthly_credit_inflow=record.average_monthly_credit_inflow,
        turnover_stability_ratio=record.turnover_stability_ratio,
        expected_utilization_ratio=record.expected_utilization_ratio,
        negative_balance_days=record.negative_balance_days,
        cleanup_days=record.cleanup_days,
        overdraft_purpose=record.overdraft_purpose,
        loan_purpose=record.loan_purpose,
        account_conduct_flags=record.account_conduct_flags or [],
        cic_bad_debt=record.cic_bad_debt,
        kyc_aml_flags=record.kyc_aml_flags or [],
        metadata=record.case_metadata or {},
    )
    return ReadinessRuleEngine().canonical_case(context)


def input_hash(context: CaseContext) -> str:
    payload = json.dumps(context.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CaseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, case_id: str) -> CaseRecord | None:
        return self.session.get(CaseRecord, case_id)

    def list(self, q: str | None = None, status: str | None = None) -> list[CaseRecord]:
        statement = select(CaseRecord).order_by(CaseRecord.created_at)
        records = list(self.session.scalars(statement))
        if q:
            needle = q.casefold()
            records = [item for item in records if needle in f"{item.name} {item.code}".casefold()]
        if status and status != "Tất cả":
            records = [item for item in records if item.display_status == status]
        return records


class AssessmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, run_id: str) -> AssessmentRunRecord | None:
        statement = (
            select(AssessmentRunRecord)
            .options(
                selectinload(AssessmentRunRecord.artifacts),
                selectinload(AssessmentRunRecord.citations),
                selectinload(AssessmentRunRecord.events),
            )
            .where(AssessmentRunRecord.run_id == run_id)
        )
        return self.session.scalar(statement)

    def get_by_idempotency(self, case_id: str, key: str) -> AssessmentRunRecord | None:
        return self.session.scalar(
            select(AssessmentRunRecord).where(
                AssessmentRunRecord.case_id == case_id,
                AssessmentRunRecord.idempotency_key == key,
            )
        )

    def latest(self, case_id: str) -> AssessmentRunRecord | None:
        return self.session.scalar(
            select(AssessmentRunRecord)
            .where(AssessmentRunRecord.case_id == case_id, AssessmentRunRecord.status == "COMPLETED")
            .order_by(AssessmentRunRecord.started_at.desc())
            .limit(1)
        )

    def list(self, case_id: str) -> list[AssessmentRunRecord]:
        return list(
            self.session.scalars(
                select(AssessmentRunRecord)
                .where(AssessmentRunRecord.case_id == case_id)
                .order_by(AssessmentRunRecord.started_at.desc())
            )
        )

    def create(self, case_id: str, key: str, context: CaseContext) -> AssessmentRunRecord:
        product_slug = context.product.value.casefold().replace("_", "-")
        record = AssessmentRunRecord(
            run_id=f"run-{uuid4().hex}",
            case_id=case_id,
            idempotency_key=key,
            input_hash=input_hash(context),
            workflow_id=f"{product_slug}-readiness",
            workflow_version="1.0.0",
            status="RUNNING",
        )
        self.session.add(record)
        self.session.commit()
        return record

    def complete(self, record: AssessmentRunRecord, state: WorkflowState) -> AssessmentRunRecord:
        record.status = "COMPLETED"
        record.route = state.route
        record.critic_verdict = state.critic_verdict
        record.final_status = state.final_status
        record.finished_at = datetime.now(timezone.utc)
        for agent_id, artifact in state.artifacts.items():
            self.session.add(
                AgentArtifactRecord(
                    artifact_id=f"artifact-{record.run_id}-{agent_id.casefold()}",
                    run_id=record.run_id,
                    agent_id=agent_id,
                    engine=artifact.engine,
                    status=artifact.status,
                    summary=artifact.summary,
                    claims=[claim.model_dump(mode="json") for claim in artifact.claims],
                    metrics=artifact.metrics,
                    warnings=artifact.warnings,
                    proposed_actions=artifact.proposed_actions,
                    raw=artifact.raw,
                )
            )
        claims_by_id = {
            claim.claim_id: claim
            for artifact in state.artifacts.values()
            for claim in artifact.claims
        }
        for claim_id, result in state.citation_results.items():
            claim = claims_by_id[claim_id]
            self.session.add(
                CitationResultRecord(
                    citation_result_id=f"citation-{record.run_id}-{claim_id}",
                    run_id=record.run_id,
                    claim_id=claim_id,
                    chunk_id=claim.chunk_id,
                    status=result.status,
                    reasons=result.reasons,
                )
            )
        # The agent runtime emits RUNNING and SUCCEEDED events for each node.
        # Persist the final event per node for the stable API/UI node timeline,
        # while keeping ordering and failure information deterministic.
        final_events: dict[str, dict] = {}
        event_order: list[str] = []
        for event in state.trace:
            node_id = event["node_id"]
            if node_id not in final_events:
                event_order.append(node_id)
            final_events[node_id] = event
        for node_id in event_order:
            event = final_events[node_id]
            timestamp = datetime.fromisoformat(event["timestamp"])
            self.session.add(
                RunEventRecord(
                    event_id=f"event-{uuid4().hex}",
                    run_id=record.run_id,
                    case_id=record.case_id,
                    node_id=event["node_id"],
                    status=event["status"],
                    engine=event["engine"],
                    input_summary=event.get("input_summary", {}),
                    output_summary=event.get("output_summary", {}),
                    timestamp=timestamp,
                )
            )
        self.session.commit()
        return self.get(record.run_id) or record

    def fail(self, record: AssessmentRunRecord, exc: Exception) -> None:
        record.status = "FAILED"
        record.final_status = "BLOCKED"
        record.error_code = type(exc).__name__
        record.error_message = str(exc)
        record.finished_at = datetime.now(timezone.utc)
        self.session.commit()


class ActionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, action_id: str) -> ProposedActionRecord | None:
        return self.session.get(ProposedActionRecord, action_id)

    def latest_for_case(self, case_id: str) -> ProposedActionRecord | None:
        return self.session.scalar(
            select(ProposedActionRecord)
            .where(ProposedActionRecord.case_id == case_id)
            .order_by(ProposedActionRecord.action_id.desc())
            .limit(1)
        )

    def get_or_create(self, case: CaseRecord, run: AssessmentRunRecord, action_type: str) -> ProposedActionRecord:
        action_id = f"act-{run.run_id}"
        existing = self.get(action_id)
        if existing:
            return existing
        payload = {
            "case_id": case.case_id,
            "case_code": case.code,
            "customer_name": case.name,
            "action_type": action_type,
            "assessment_run_id": run.run_id,
            "owner": case.owner,
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        record = ProposedActionRecord(
            action_id=action_id,
            case_id=case.case_id,
            run_id=run.run_id,
            action_type=action_type,
            payload=payload,
            payload_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        )
        self.session.add(record)
        self.session.commit()
        return record


def run_schema(record: AssessmentRunRecord) -> AssessmentRun:
    return AssessmentRun.model_validate(record, from_attributes=True)


def action_schema(record: ProposedActionRecord) -> ProposedAction:
    return ProposedAction(
        id=record.action_id,
        case_id=record.case_id,
        run_id=record.run_id,
        type=record.action_type,
        payload=record.payload,
        payload_hash=record.payload_hash,
        status=record.status,
        created_by=record.created_by,
        approved_by=record.approved_by,
        decided_at=record.decided_at,
    )
