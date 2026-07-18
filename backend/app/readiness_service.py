from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from nexusops_agent.contracts.evidence import ValidationResult
from sqlalchemy import select
from sqlalchemy.orm import Session

from .exceptions import DomainError
from .models import AgentArtifactRecord, AssessmentRunRecord, CaseRecord
from .readiness_schemas import CreateReadinessCase, EvidenceItem, ReadinessCase, ReadinessTraceEvent, ReadinessWorkflow
from .repositories import AssessmentRepository, CaseRepository, case_context_from_record, input_hash
from .services import AssessmentService


def _text(value: object | None) -> str:
    return "" if value is None else str(value)


def _domain(chunk) -> str:
    if chunk.quality.status == "REVIEW_REQUIRED":
        return "QUARANTINE"
    if chunk.quality.status == "DEMO_ONLY" or chunk.is_synthetic:
        return "DEMO_POLICY"
    if chunk.domain == "COMPLIANCE_AML":
        return "AML"
    return "LENDING"


def _source_type(chunk) -> str:
    if chunk.is_synthetic or chunk.quality.status == "DEMO_ONLY":
        return "DEMO_CONTENT"
    if chunk.source_type and "REG" in chunk.source_type.upper():
        return "REGULATION"
    return "INTERNAL_POLICY"


class ReadinessService:
    def __init__(self, session: Session, assessments: AssessmentService) -> None:
        self.session = session
        self.assessments = assessments
        self.cases = CaseRepository(session)
        self.runs = AssessmentRepository(session)

    def list(self, q: str | None = None, product: str | None = None, status: str | None = None) -> list[ReadinessCase]:
        records = self.cases.list(q)
        output: list[ReadinessCase] = []
        for record in records:
            if product and record.product != product:
                continue
            item = self.get(record.case_id)
            if status and item.workflow.final_status != status:
                continue
            output.append(item)
        return output

    def get(self, case_id: str) -> ReadinessCase:
        record = self.cases.get(case_id)
        if record is None:
            raise DomainError(404, "CASE_NOT_FOUND", "Case not found")
        run = self.assessments.latest_or_run(case_id)
        return self._build(record, run)

    def create(self, payload: CreateReadinessCase, idempotency_key: str | None = None) -> ReadinessCase:
        if self.cases.get(payload.context.case_id) is not None:
            raise DomainError(409, "CASE_ALREADY_EXISTS", "Case already exists")
        context = payload.context
        display_amount = f"₫{context.requested_amount:,.0f}"
        record = CaseRecord(
            case_id=context.case_id,
            customer_id=context.customer_id,
            code=context.case_id,
            name=payload.company_name,
            short_name=payload.company_name[:80],
            owner=payload.owner,
            display_amount=display_amount,
            purpose=context.product.value,
            sla="02:15:00",
            submitted_label=datetime.now(timezone.utc).isoformat(),
            agent_label="NexusOps-Agent",
            score=0,
            display_status="Đang chờ rà soát",
            risk="Cao" if context.cic_bad_debt else "Trung bình",
            issue="Readiness assessment đang được xử lý",
            existing_customer=context.existing_customer,
            product=context.product.value,
            requested_amount=context.requested_amount,
            relationship_months=context.relationship_months,
            submitted_documents=context.submitted_documents,
            required_documents=context.required_documents,
            annual_revenue=context.annual_revenue,
            pretax_profit_last_2_years=context.pretax_profit_last_2_years,
            tax_declared_revenue=context.tax_declared_revenue,
            cic_bad_debt=context.cic_bad_debt,
            kyc_aml_flags=context.kyc_aml_flags,
            case_metadata=context.metadata,
        )
        self.session.add(record)
        self.session.commit()
        key = idempotency_key or f"create-{context.case_id}-{input_hash(context)}"
        self.assessments.run(context.case_id, key)
        return self.get(context.case_id)

    def _build(self, record: CaseRecord, run: AssessmentRunRecord) -> ReadinessCase:
        context = case_context_from_record(record)
        artifacts = {artifact.agent_id: self._artifact(artifact) for artifact in run.artifacts}
        citation_results = self._citation_results(run)
        traces = [
            ReadinessTraceEvent(
                node=event.node_id,
                status="COMPLETED" if event.status == "SUCCEEDED" else event.status,
                started_at=event.timestamp.isoformat(),
                duration_ms=None,
                message=event.output_summary.get("artifact_status", event.status),
            )
            for event in run.events
        ]
        evidence = self._evidence(record, context, run, citation_results)
        workflow = ReadinessWorkflow(
            case=context,
            route=run.route,
            artifacts=artifacts,
            citation_results=citation_results,
            critic_verdict=run.critic_verdict,
            final_status=run.final_status,
            trace=traces,
        )
        return ReadinessCase(
            id=record.case_id,
            company_name=record.name,
            owner=record.owner,
            submitted_at=record.created_at.isoformat(),
            sla_due=record.sla,
            context=context,
            workflow=workflow,
            evidence=evidence,
        )

    @staticmethod
    def _artifact(record: AgentArtifactRecord):
        from nexusops_agent.contracts.state import AgentArtifact

        return AgentArtifact(
            agent_id=record.agent_id,
            engine=record.engine,
            status=record.status,
            summary=record.summary,
            claims=record.claims,
            metrics=record.metrics,
            warnings=record.warnings,
            proposed_actions=record.proposed_actions,
            raw=record.raw,
        )

    @staticmethod
    def _citation_results(run: AssessmentRunRecord) -> dict[str, ValidationResult]:
        return {
            record.claim_id: ValidationResult(status=record.status, reasons=record.reasons)
            for record in run.citations
        }

    def _evidence(self, record: CaseRecord, context, run: AssessmentRunRecord, results: dict[str, ValidationResult]) -> list[EvidenceItem]:
        items = [
            EvidenceItem(
                chunk_id=f"{record.case_id}-CASE-DATA",
                document_id=record.case_id,
                document_number=record.case_id,
                document_title="Case intake data",
                domain="CASE_DATA",
                source_type="CASE_RECORD",
                source_authority="NexusOps Case Service",
                validity_status="CURRENT_SNAPSHOT",
                effective_date=record.created_at.date().isoformat(),
                page_or_part="CaseContext",
                citation_text=f"Case {record.case_id} có {len(context.submitted_documents)}/{len(context.required_documents)} tài liệu đã nộp.",
                full_content=context.model_dump_json(),
                evaluation_basis="Đối chiếu trực tiếp dữ liệu CaseContext với output của workflow.",
                content_hash=f"sha256:{input_hash(context)}",
                quality_status="ACCEPTED",
                validation="VALID",
                reasons=[],
                related_nodes=run.route,
                case_field_refs=["existing_customer", "product", "requested_amount", "submitted_documents", "required_documents"],
                provenance={"captured_by": "case-service", "source": "SQLite"},
            )
        ]
        claims = [claim for artifact in run.artifacts for claim in artifact.claims]
        corpus = self.assessments.agent_service.corpus.by_id()
        for claim in claims:
            chunk = corpus.get(claim["chunk_id"])
            if chunk is None:
                continue
            validation = results.get(claim["claim_id"], ValidationResult(status="ABSTAIN_NO_EVIDENCE", reasons=["NOT_VALIDATED"]))
            related_nodes = [artifact.agent_id for artifact in run.artifacts if any(item.get("chunk_id") == chunk.chunk_id for item in artifact.claims)]
            items.append(
                EvidenceItem(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_number=chunk.document_number,
                    document_title=chunk.document_title or chunk.title or chunk.document_number,
                    domain=_domain(chunk),
                    source_type=_source_type(chunk),
                    source_authority=chunk.source_authority,
                    validity_status=chunk.validity_status,
                    effective_date=_text(chunk.effective_from or chunk.issue_date),
                    article=chunk.article,
                    clause=chunk.clause,
                    page_or_part=_text(chunk.page_or_part),
                    citation_text=chunk.citation_text,
                    full_content=chunk.content,
                    evaluation_basis=_text(chunk.provenance.get("evaluation_basis")),
                    content_hash=chunk.content_hash,
                    quality_status=chunk.quality.status,
                    validation=validation.status,
                    reasons=validation.reasons,
                    related_nodes=related_nodes,
                    case_field_refs=[],
                    provenance={key: _text(value) for key, value in chunk.provenance.items()},
                )
            )
        return items
