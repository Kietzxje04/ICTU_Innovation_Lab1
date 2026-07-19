import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.approval_service import LoanApprovalService
from app.auth import CurrentUser, role_can_approve, verify_password
from app.exceptions import DomainError
from app.database import Base
from app.models import RoleRecord, UserRecord
from app.seed import seed_cases


class RbacApprovalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            seed_cases(session)

    def test_seeded_account_counts_and_passwords(self) -> None:
        with Session(self.engine) as session:
            counts = {
                role: len(list(session.scalars(select(UserRecord).where(UserRecord.role_id == role))))
                for role in ("DIRECTOR", "MANAGER", "EMPLOYEE")
            }
            self.assertEqual({"DIRECTOR": 1, "MANAGER": 3, "EMPLOYEE": 5}, counts)
            employee = session.scalar(select(UserRecord).where(UserRecord.username == "employee-1"))
            self.assertTrue(employee and verify_password("NexusOps@2026", employee.password_hash))

    def test_approval_limits(self) -> None:
        self.assertTrue(role_can_approve("EMPLOYEE", 499_999_999))
        self.assertFalse(role_can_approve("EMPLOYEE", 500_000_000))
        self.assertTrue(role_can_approve("MANAGER", 999_999_999))
        self.assertFalse(role_can_approve("MANAGER", 1_000_000_000))
        self.assertTrue(role_can_approve("DIRECTOR", 100_000_000))
        self.assertTrue(role_can_approve("DIRECTOR", 499_999_999))
        self.assertTrue(role_can_approve("DIRECTOR", 999_999_999))
        self.assertTrue(role_can_approve("DIRECTOR", 1_000_000_000))
        self.assertTrue(role_can_approve("DIRECTOR", 10_000_000_000))

    def test_large_loan_transfers_employee_manager_director(self) -> None:
        with Session(self.engine) as session:
            users = {user.username: user for user in session.scalars(select(UserRecord))}
            roles = {role.role_id: role for role in session.scalars(select(RoleRecord))}
            service = LoanApprovalService(session)
            first = service.transfer("hung-phat", CurrentUser(users["employee-1"], roles["EMPLOYEE"]), "Vượt hạn mức nhân viên", "manager-1")
            second = service.transfer("hung-phat", CurrentUser(users["manager-1"], roles["MANAGER"]), "Vượt hạn mức quản lý", "director-1")
            self.assertEqual("MANAGER", first["current_role"])
            self.assertEqual("DIRECTOR", second["current_role"])

    def test_higher_role_cannot_bypass_required_transfer(self) -> None:
        with Session(self.engine) as session:
            users = {user.username: user for user in session.scalars(select(UserRecord))}
            roles = {role.role_id: role for role in session.scalars(select(RoleRecord))}
            service = LoanApprovalService(session)
            status = service.check("hung-phat", CurrentUser(users["director-1"], roles["DIRECTOR"]))
            self.assertFalse(status["can_approve"])
            with self.assertRaises(DomainError) as context:
                service.approve("hung-phat", CurrentUser(users["director-1"], roles["DIRECTOR"]), "Không được bỏ qua luồng chuyển cấp")
            self.assertEqual("APPROVAL_NOT_ASSIGNED", context.exception.code)


if __name__ == "__main__":
    unittest.main()
