import unittest
import os

os.environ.setdefault("NEXUSOPS_ENV", "test")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agent_service import AgentService
from app.database import Base
from app.exceptions import DomainError
from app.seed import seed_cases
from app.services import ActionService, AssessmentService, ResolutionService


class AgentIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine, expire_on_commit=False)
        session = cls.Session()
        try:
            seed_cases(session)
        finally:
            session.close()
        cls.agent = AgentService()

    @classmethod
    def tearDownClass(cls) -> None:
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()

    def setUp(self) -> None:
        self.session = self.Session()
        self.assessments = AssessmentService(self.session, self.agent)
        self.resolution = ResolutionService(self.session, self.assessments)
        self.actions = ActionService(self.session, self.resolution)

    def tearDown(self) -> None:
        self.session.close()

    def test_assessment_is_persisted_and_idempotent(self) -> None:
        first = self.assessments.run("toan-cau", "assessment-idempotency-test")
        second = self.assessments.run("toan-cau", "assessment-idempotency-test")
        self.assertEqual(first.run_id, second.run_id)
        self.assertEqual("COMPLETED", first.status)
        self.assertEqual(["MANDATORY_CRITIC", "CITATION_VALIDATOR", "READINESS_RULE_ENGINE", "POLICY_GATE"], first.route[-4:])
        self.assertGreaterEqual(len(first.artifacts), 10)
        self.assertEqual(len(first.artifacts), len(first.events))

    def test_resolution_and_action_are_agent_backed(self) -> None:
        package = self.resolution.get("le-gia")
        self.assertEqual("DOCUMENT_REQUIRED", package.primary_outcome)
        self.assertEqual("REQUEST_MISSING_DOCUMENTS", package.proposed_action.type)
        approved = self.actions.approve(
            "le-gia",
            package.proposed_action.id,
            package.proposed_action.payload_hash,
            "test-manager",
            "manager",
            "approve-le-gia-once",
            "Test approval",
        )
        repeated = self.actions.approve(
            "le-gia",
            package.proposed_action.id,
            package.proposed_action.payload_hash,
            "test-manager",
            "manager",
            "approve-le-gia-once",
            "Test approval",
        )
        self.assertEqual("SUCCEEDED", approved.status)
        self.assertEqual(approved.id, repeated.id)

    def test_unauthorized_approval_is_blocked(self) -> None:
        package = self.resolution.get("hung-phat")
        with self.assertRaises(DomainError) as context:
            self.actions.approve(
                "hung-phat",
                package.proposed_action.id,
                package.proposed_action.payload_hash,
                "viewer-user",
                "viewer",
                "unauthorized-key",
                None,
            )
        self.assertEqual(403, context.exception.status_code)


if __name__ == "__main__":
    unittest.main()
