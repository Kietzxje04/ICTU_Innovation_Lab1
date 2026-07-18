from __future__ import annotations

import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, engine as runtime_engine, get_session
from app.main import app
from app.seed import seed_cases


class FullApiTest(unittest.TestCase):
    """One end-to-end API contract test using an isolated in-memory database."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)
        session = cls.SessionLocal()
        try:
            seed_cases(session)
        finally:
            session.close()

        def override_session():
            session: Session = cls.SessionLocal()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_session] = override_session
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        app.dependency_overrides.clear()
        Base.metadata.drop_all(cls.engine)
        cls.engine.dispose()
        runtime_engine.dispose()

    def assert_success(self, response, expected_status: int = 200):
        self.assertEqual(expected_status, response.status_code, response.text)
        payload = response.json()
        self.assertIsNone(payload["error"])
        self.assertIn("request_id", payload["meta"])
        self.assertEqual("single-backend", payload["meta"]["api"])
        self.assertEqual(payload["meta"]["request_id"], response.headers["X-Request-Id"])
        return payload

    def assert_error(self, response, expected_status: int, expected_code: str):
        self.assertEqual(expected_status, response.status_code, response.text)
        payload = response.json()
        self.assertIsNone(payload["data"])
        self.assertEqual(expected_code, payload["error"]["code"])
        self.assertIn("request_id", payload["meta"])
        return payload

    def test_full_api_flow(self) -> None:
        # Platform and Agent Layer health.
        health = self.assert_success(self.client.get("/health"))
        self.assertEqual("ok", health["data"]["status"])
        self.assertEqual(240, health["data"]["agent"]["rag_records"])

        agent_health = self.assert_success(self.client.get("/api/agent/health"))
        self.assertEqual("deterministic", agent_health["data"]["mode"])

        inventory = self.assert_success(self.client.get("/api/agent/rag/inventory"))
        self.assertEqual(240, inventory["data"]["total"])
        self.assertEqual(25, inventory["data"]["quality"]["ACCEPTED"])
        self.assertEqual(213, inventory["data"]["quality"]["REVIEW_REQUIRED"])

        # Case catalogue, search and consistent errors.
        cases = self.assert_success(self.client.get("/api/cases"))
        self.assertEqual(4, cases["meta"]["total"])
        self.assertEqual({"toan-cau", "hung-phat", "sai-gon", "le-gia"}, {item["id"] for item in cases["data"]})

        filtered = self.assert_success(self.client.get("/api/cases", params={"q": "Toàn cầu"}))
        self.assertEqual(1, filtered["meta"]["total"])
        self.assertEqual("toan-cau", filtered["data"][0]["id"])

        case = self.assert_success(self.client.get("/api/cases/toan-cau"))
        self.assertEqual("HS-2023-8901", case["data"]["code"])
        self.assert_error(self.client.get("/api/cases/not-found"), 404, "CASE_NOT_FOUND")
        self.assertEqual(404, self.client.get("/api/v1/cases").status_code)

        # Assessment run and request idempotency.
        idempotency_key = f"full-api-run-{uuid4().hex}"
        run_response = self.client.post(
            "/api/cases/toan-cau/assessment-runs",
            headers={"Idempotency-Key": idempotency_key, "X-Request-Id": "full-api-request"},
        )
        run = self.assert_success(run_response)
        self.assertEqual("full-api-request", run["meta"]["request_id"])
        self.assertEqual("COMPLETED", run["data"]["status"])
        self.assertEqual("NEEDS_MORE_EVIDENCE", run["data"]["final_status"])
        self.assertEqual(["MANDATORY_CRITIC", "CITATION_VALIDATOR", "POLICY_GATE"], run["data"]["route"][-3:])
        run_id = run["data"]["run_id"]

        repeated_run = self.assert_success(
            self.client.post(
                "/api/cases/toan-cau/assessment-runs",
                headers={"Idempotency-Key": idempotency_key},
            )
        )
        self.assertEqual(run_id, repeated_run["data"]["run_id"])

        self.assert_error(
            self.client.post("/api/cases/toan-cau/assessment-runs"),
            422,
            "VALIDATION_ERROR",
        )

        runs = self.assert_success(self.client.get("/api/cases/toan-cau/assessment-runs"))
        self.assertEqual(1, runs["meta"]["total"])

        run_detail = self.assert_success(self.client.get(f"/api/cases/toan-cau/assessment-runs/{run_id}"))
        self.assertEqual(run_id, run_detail["data"]["run_id"])

        artifacts = self.assert_success(self.client.get(f"/api/cases/toan-cau/assessment-runs/{run_id}/artifacts"))
        artifact_ids = {item["agent_id"] for item in artifacts["data"]}
        self.assertGreaterEqual(artifacts["meta"]["total"], 10)
        self.assertTrue({"PLANNER_AGENT", "MANDATORY_CRITIC", "CITATION_VALIDATOR", "POLICY_GATE"}.issubset(artifact_ids))

        events = self.assert_success(self.client.get(f"/api/cases/toan-cau/assessment-runs/{run_id}/events"))
        self.assertEqual(artifacts["meta"]["total"], events["meta"]["total"])
        self.assertEqual("POLICY_GATE", events["data"][-1]["node_id"])

        case_events = self.assert_success(self.client.get("/api/cases/toan-cau/events"))
        self.assertEqual(events["meta"]["total"], case_events["meta"]["total"])

        # Resolution and governed action lifecycle.
        resolution = self.assert_success(self.client.get("/api/cases/toan-cau/resolution-package"))
        self.assertEqual(run_id, resolution["data"]["run"]["run_id"])
        self.assertEqual("DOCUMENT_REQUIRED", resolution["data"]["primary_outcome"])
        self.assertEqual("REQUEST_MISSING_DOCUMENTS", resolution["data"]["proposed_action"]["type"])
        action = resolution["data"]["proposed_action"]

        actions = self.assert_success(self.client.get("/api/cases/toan-cau/actions"))
        self.assertEqual(1, actions["meta"]["total"])
        self.assertEqual(action["id"], actions["data"][0]["id"])

        approval_url = f"/api/cases/toan-cau/actions/{action['id']}/approve"
        approval_body = {"approved_payload_hash": action["payload_hash"], "reason": "Full API test"}
        self.assert_error(
            self.client.post(
                approval_url,
                headers={"Idempotency-Key": "full-api-unauthorized"},
                json=approval_body,
            ),
            403,
            "INSUFFICIENT_ROLE",
        )
        self.assert_error(
            self.client.post(
                approval_url,
                headers={
                    "Idempotency-Key": "full-api-wrong-hash",
                    "X-User-Id": "manager-1",
                    "X-Role": "manager",
                },
                json={"approved_payload_hash": "wrong-hash"},
            ),
            409,
            "PAYLOAD_HASH_MISMATCH",
        )

        approval_headers = {
            "Idempotency-Key": "full-api-approve-once",
            "X-User-Id": "manager-1",
            "X-Role": "manager",
        }
        approved = self.assert_success(self.client.post(approval_url, headers=approval_headers, json=approval_body))
        repeated_approval = self.assert_success(self.client.post(approval_url, headers=approval_headers, json=approval_body))
        self.assertEqual("SUCCEEDED", approved["data"]["status"])
        self.assertEqual(approved["data"]["id"], repeated_approval["data"]["id"])

        execution = self.assert_success(
            self.client.get(f"/api/cases/toan-cau/actions/{action['id']}/execution")
        )
        self.assertEqual("SUCCEEDED", execution["data"]["status"])
        self.assertEqual("full-api-approve-once", execution["data"]["idempotency_key"])

        self.assert_error(
            self.client.post(
                f"/api/cases/toan-cau/actions/{action['id']}/reject",
                headers={"X-User-Id": "manager-1", "X-Role": "manager"},
                json={"reason": "Cannot reject after execution"},
            ),
            409,
            "ACTION_ALREADY_EXECUTED",
        )

        rejected_package = self.assert_success(self.client.get("/api/cases/le-gia/resolution-package"))
        rejected_action = rejected_package["data"]["proposed_action"]
        reject_url = f"/api/cases/le-gia/actions/{rejected_action['id']}/reject"
        reject_headers = {"X-User-Id": "manager-1", "X-Role": "manager"}
        rejected = self.assert_success(
            self.client.post(reject_url, headers=reject_headers, json={"reason": "Need manual review"})
        )
        repeated_reject = self.assert_success(
            self.client.post(reject_url, headers=reject_headers, json={"reason": "Need manual review"})
        )
        self.assertEqual("REJECTED", rejected["data"]["status"])
        self.assertEqual(rejected["data"]["id"], repeated_reject["data"]["id"])

        # Rerun creates a new immutable AssessmentRun.
        rerun = self.assert_success(self.client.post("/api/cases/toan-cau/assessment-runs/rerun"))
        self.assertNotEqual(run_id, rerun["data"]["run_id"])
        runs_after_rerun = self.assert_success(self.client.get("/api/cases/toan-cau/assessment-runs"))
        self.assertEqual(2, runs_after_rerun["meta"]["total"])

        # Browser CORS contract.
        cors = self.client.options(
            "/api/cases",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(200, cors.status_code)
        self.assertEqual("http://localhost:5173", cors.headers["access-control-allow-origin"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
