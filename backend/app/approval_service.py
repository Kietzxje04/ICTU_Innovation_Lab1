from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import CurrentUser, next_role, role_at_least, role_can_approve
from .exceptions import DomainError
from .models import CaseRecord, LoanApprovalRecord, UserRecord
from .repositories import AssessmentRepository


class LoanApprovalService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.runs = AssessmentRepository(session)

    def _case(self, case_id: str) -> CaseRecord:
        case = self.session.get(CaseRecord, case_id)
        if not case:
            raise DomainError(404, "CASE_NOT_FOUND", "Không tìm thấy hồ sơ")
        return case

    def _record(self, case_id: str) -> LoanApprovalRecord:
        record = self.session.scalar(select(LoanApprovalRecord).where(LoanApprovalRecord.case_id == case_id))
        if record:
            return record
        record = LoanApprovalRecord(approval_id=f"approval-{uuid4().hex}", case_id=case_id, current_role="EMPLOYEE")
        self.session.add(record)
        self.session.commit()
        return record

    def _readiness(self, case_id: str) -> tuple[bool, list[str]]:
        run = self.runs.latest(case_id)
        if not run:
            return False, ["Hồ sơ chưa chạy quy trình kiểm tra điều kiện"]
        reasons: list[str] = []
        if run.final_status != "READY_FOR_HUMAN_REVIEW":
            reasons.append("Hồ sơ chưa đạt trạng thái sẵn sàng để chuyên viên rà soát")
        if run.critic_verdict != "PASS":
            reasons.append("Khâu phản biện bắt buộc chưa đạt")
        return not reasons, reasons

    def check(self, case_id: str, user: CurrentUser) -> dict[str, object]:
        case = self._case(case_id)
        record = self._record(case_id)
        ready, blockers = self._readiness(case_id)
        assigned_role = record.current_role
        is_assigned = (
            role_at_least(user.role.role_id, assigned_role)
            and (record.assigned_to is None or record.assigned_to == user.record.user_id)
        )
        can_approve = ready and is_assigned and role_can_approve(user.role.role_id, case.requested_amount)
        can_transfer = (
            ready
            and record.status != "APPROVED"
            and is_assigned
            and not role_can_approve(user.role.role_id, case.requested_amount)
        )
        required_role = "EMPLOYEE" if case.requested_amount < 500_000_000 else "MANAGER" if case.requested_amount < 1_000_000_000 else "DIRECTOR"
        return {
            "case_id": case_id,
            "amount": case.requested_amount,
            "status": record.status,
            "current_role": assigned_role,
            "required_role": required_role,
            "assigned_to": record.assigned_to,
            "ready": ready,
            "blockers": blockers,
            "can_approve": can_approve,
            "can_transfer": can_transfer,
            "must_transfer": ready and not role_can_approve(assigned_role, case.requested_amount),
            "permissions": user.role.permissions,
        }

    def approve(self, case_id: str, user: CurrentUser, reason: str | None) -> dict[str, object]:
        case = self._case(case_id)
        record = self._record(case_id)
        status = self.check(case_id, user)
        if record.status == "APPROVED":
            return self.serialize(record)
        if not status["ready"]:
            raise DomainError(409, "LOAN_NOT_READY", "Hồ sơ chưa đủ điều kiện phê duyệt", status["blockers"])
        if not role_at_least(user.role.role_id, record.current_role) or (record.assigned_to and record.assigned_to != user.record.user_id):
            raise DomainError(403, "APPROVAL_NOT_ASSIGNED", "Hồ sơ chưa được phân công cho người dùng hoặc cấp thẩm quyền này")
        if not role_can_approve(user.role.role_id, case.requested_amount):
            raise DomainError(403, "APPROVAL_LIMIT_EXCEEDED", "Giá trị khoản vay vượt thẩm quyền; vui lòng chuyển hồ sơ lên cấp trên")
        now = datetime.now(timezone.utc)
        record.status = "APPROVED"
        record.approved_by = user.record.user_id
        record.decision_reason = reason
        record.history = [*record.history, {"action": "APPROVE", "by": user.record.user_id, "role": user.role.role_id, "at": now.isoformat(), "reason": reason}]
        case.display_status = "Đã duyệt"
        self.session.commit()
        return self.serialize(record)

    def transfer(self, case_id: str, user: CurrentUser, reason: str, target_user_id: str | None) -> dict[str, object]:
        case = self._case(case_id)
        record = self._record(case_id)
        status = self.check(case_id, user)
        if record.status == "APPROVED":
            raise DomainError(409, "LOAN_ALREADY_APPROVED", "Hồ sơ đã được phê duyệt")
        if not status["ready"]:
            raise DomainError(409, "LOAN_NOT_READY", "Hồ sơ chưa đủ điều kiện để chuyển cấp", status["blockers"])
        if not role_at_least(user.role.role_id, record.current_role) or (record.assigned_to and record.assigned_to != user.record.user_id):
            raise DomainError(403, "TRANSFER_NOT_ASSIGNED", "Chỉ cấp đang xử lý hồ sơ mới được chuyển tiếp")
        target_role = next_role(record.current_role)
        if not target_role:
            raise DomainError(409, "NO_HIGHER_APPROVAL_LEVEL", "Không còn cấp phê duyệt cao hơn")
        if role_can_approve(user.role.role_id, case.requested_amount):
            raise DomainError(409, "TRANSFER_NOT_REQUIRED", "Khoản vay vẫn nằm trong thẩm quyền của bạn")
        target = self.session.get(UserRecord, target_user_id) if target_user_id else self.session.scalar(select(UserRecord).where(UserRecord.role_id == target_role, UserRecord.is_active.is_(True)).order_by(UserRecord.username))
        if not target or target.role_id != target_role or not target.is_active:
            raise DomainError(400, "INVALID_TRANSFER_TARGET", "Người nhận không thuộc cấp phê duyệt kế tiếp")
        now = datetime.now(timezone.utc)
        record.current_role = target_role
        record.assigned_to = target.user_id
        record.status = "TRANSFERRED"
        record.history = [*record.history, {"action": "TRANSFER", "by": user.record.user_id, "from_role": user.role.role_id, "to_role": target_role, "to_user": target.user_id, "at": now.isoformat(), "reason": reason}]
        self.session.commit()
        return self.serialize(record)

    @staticmethod
    def serialize(record: LoanApprovalRecord) -> dict[str, object]:
        return {
            "approval_id": record.approval_id,
            "case_id": record.case_id,
            "status": record.status,
            "current_role": record.current_role,
            "assigned_to": record.assigned_to,
            "approved_by": record.approved_by,
            "decision_reason": record.decision_reason,
            "history": record.history,
        }
