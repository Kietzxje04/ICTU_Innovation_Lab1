from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from nexusops_agent.evaluation import EvaluationRunner
from nexusops_agent.orchestration.workflow import WorkflowDefinition
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .exceptions import DomainError
from .models import EvaluationRunRecord, MockExternalActionRecord, WorkflowTemplateRecord
from .v3_schemas import WorkflowCreate, WorkflowView


REQUIRED_WORKFLOW_NODES = {
    "EXISTING_CUSTOMER_GATE",
    "PRODUCT_AGENT",
    "DOCUMENT_COMPLETENESS",
    "READINESS_RULE_ENGINE",
    "MANDATORY_CRITIC",
    "CITATION_VALIDATOR",
    "POLICY_GATE",
}
MANDATORY_TAIL = ["MANDATORY_CRITIC", "CITATION_VALIDATOR", "READINESS_RULE_ENGINE", "POLICY_GATE"]


def _definition_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_workflow_payload(payload: WorkflowCreate) -> list[str]:
    errors: list[str] = []
    try:
        WorkflowDefinition.model_validate(payload.model_dump()).validate_safety()
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
    missing = sorted(REQUIRED_WORKFLOW_NODES - set(payload.nodes))
    if missing:
        errors.append(f"Missing required nodes: {missing}")
    if len(payload.nodes) != len(set(payload.nodes)):
        errors.append("Workflow nodes must be unique")
    if payload.nodes[-4:] != MANDATORY_TAIL:
        errors.append(f"Workflow must end with {MANDATORY_TAIL}")
    if payload.product == "CORPORATE_OVERDRAFT" and "ACCOUNT_TURNOVER" not in payload.nodes:
        errors.append("Corporate Overdraft workflow requires ACCOUNT_TURNOVER")
    if payload.product == "WORKING_CAPITAL":
        product_nodes = {"FINANCIAL_METRICS", "TAX_CONSISTENCY", "CREDIT_AGENT"}
        missing_product = sorted(product_nodes - set(payload.nodes))
        if missing_product:
            errors.append(f"Working Capital workflow missing nodes: {missing_product}")
    return list(dict.fromkeys(errors))


class WorkflowRegistryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._seed_published_workflows()

    def _seed_published_workflows(self) -> None:
        config_dir = get_settings().agent_root / "configs" / "workflows"
        for path in sorted(config_dir.glob("*.json")):
            payload = WorkflowCreate.model_validate(json.loads(path.read_text(encoding="utf-8")))
            record_id = f"{payload.workflow_id}:{payload.version}"
            if self.session.get(WorkflowTemplateRecord, record_id) is not None:
                continue
            errors = validate_workflow_payload(payload)
            record = WorkflowTemplateRecord(
                record_id=record_id,
                workflow_id=payload.workflow_id,
                version=payload.version,
                product=payload.product,
                nodes=payload.nodes,
                max_rework=payload.max_rework,
                status="PUBLISHED" if not errors else "DRAFT",
                definition_hash=_definition_hash(payload.model_dump(mode="json")),
                validation_errors=errors,
                created_by="agent-config",
                published_at=datetime.now(timezone.utc) if not errors else None,
            )
            self.session.add(record)
        self.session.commit()

    @staticmethod
    def view(record: WorkflowTemplateRecord) -> WorkflowView:
        return WorkflowView(
            workflow_id=record.workflow_id,
            version=record.version,
            product=record.product,
            nodes=record.nodes,
            max_rework=record.max_rework,
            status=record.status,
            definition_hash=record.definition_hash,
            validation_errors=record.validation_errors,
            created_by=record.created_by,
            created_at=record.created_at,
            published_at=record.published_at,
        )

    def list(self) -> list[WorkflowView]:
        records = self.session.scalars(
            select(WorkflowTemplateRecord).order_by(
                WorkflowTemplateRecord.workflow_id,
                WorkflowTemplateRecord.created_at.desc(),
            )
        )
        return [self.view(record) for record in records]

    def versions(self, workflow_id: str) -> list[WorkflowView]:
        records = list(
            self.session.scalars(
                select(WorkflowTemplateRecord)
                .where(WorkflowTemplateRecord.workflow_id == workflow_id)
                .order_by(WorkflowTemplateRecord.created_at.desc())
            )
        )
        if not records:
            raise DomainError(404, "WORKFLOW_NOT_FOUND", "Workflow not found")
        return [self.view(record) for record in records]

    def create(self, payload: WorkflowCreate, created_by: str) -> WorkflowView:
        record_id = f"{payload.workflow_id}:{payload.version}"
        if self.session.get(WorkflowTemplateRecord, record_id):
            raise DomainError(409, "WORKFLOW_VERSION_EXISTS", "Workflow version already exists")
        errors = validate_workflow_payload(payload)
        record = WorkflowTemplateRecord(
            record_id=record_id,
            workflow_id=payload.workflow_id,
            version=payload.version,
            product=payload.product,
            nodes=payload.nodes,
            max_rework=payload.max_rework,
            status="DRAFT",
            definition_hash=_definition_hash(payload.model_dump(mode="json")),
            validation_errors=errors,
            created_by=created_by,
        )
        self.session.add(record)
        self.session.commit()
        return self.view(record)

    def _latest(self, workflow_id: str) -> WorkflowTemplateRecord:
        record = self.session.scalar(
            select(WorkflowTemplateRecord)
            .where(WorkflowTemplateRecord.workflow_id == workflow_id)
            .order_by(WorkflowTemplateRecord.created_at.desc())
            .limit(1)
        )
        if record is None:
            raise DomainError(404, "WORKFLOW_NOT_FOUND", "Workflow not found")
        return record

    def validate(self, workflow_id: str) -> WorkflowView:
        record = self._latest(workflow_id)
        payload = WorkflowCreate(
            workflow_id=record.workflow_id,
            version=record.version,
            product=record.product,
            nodes=record.nodes,
            max_rework=record.max_rework,
        )
        record.validation_errors = validate_workflow_payload(payload)
        self.session.commit()
        return self.view(record)

    def publish(self, workflow_id: str) -> WorkflowView:
        record = self._latest(workflow_id)
        validated = self.validate(workflow_id)
        if validated.validation_errors:
            raise DomainError(
                422,
                "WORKFLOW_VALIDATION_FAILED",
                "Workflow cannot be published",
                validated.validation_errors,
            )
        record.status = "PUBLISHED"
        record.published_at = datetime.now(timezone.utc)
        self.session.commit()
        return self.view(record)


class EvaluationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run(self) -> EvaluationRunRecord:
        path = get_settings().agent_root / "evaluation" / "golden_cases.json"
        report = EvaluationRunner().run_file(Path(path))
        record = EvaluationRunRecord(
            run_id=f"eval-{uuid4().hex}",
            scenario_count=report["scenario_count"],
            passed=report["passed"],
            failed=report["failed"],
            report=report,
        )
        self.session.add(record)
        self.session.commit()
        return record

    def get(self, run_id: str) -> EvaluationRunRecord:
        record = self.session.get(EvaluationRunRecord, run_id)
        if record is None:
            raise DomainError(404, "EVALUATION_NOT_FOUND", "Evaluation run not found")
        return record


class MockActionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def execute(
        self,
        *,
        action_type: str,
        case_id: str,
        payload: dict[str, object],
        idempotency_key: str,
        approved_by: str,
    ) -> MockExternalActionRecord:
        existing = self.session.scalar(
            select(MockExternalActionRecord).where(
                MockExternalActionRecord.idempotency_key == idempotency_key
            )
        )
        if existing:
            if existing.action_type != action_type or existing.case_id != case_id:
                raise DomainError(409, "IDEMPOTENCY_KEY_REUSED", "Idempotency key belongs to another action")
            return existing
        digest = hashlib.sha256(f"{action_type}:{case_id}:{idempotency_key}".encode()).hexdigest()[:20]
        record = MockExternalActionRecord(
            external_ref=f"mock-{digest}",
            idempotency_key=idempotency_key,
            action_type=action_type,
            case_id=case_id,
            payload=dict(payload),
            approved_by=approved_by,
        )
        self.session.add(record)
        self.session.commit()
        return record

    def get(self, external_ref: str) -> MockExternalActionRecord:
        record = self.session.get(MockExternalActionRecord, external_ref)
        if record is None:
            raise DomainError(404, "MOCK_ACTION_NOT_FOUND", "Mock action not found")
        return record
