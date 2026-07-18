import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.enums import ProductType
from nexusops_agent.contracts.state import WorkflowState
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.rag.retriever import HybridLiteRetriever
from nexusops_agent.services.agent_service import AgentService
from nexusops_agent.workflows.runner import AgentWorkflowRunner


class CriticHitlServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        corpus = RagCorpus(ROOT / "final_rag_data_normalized_v1.json")
        cls.service = AgentService(
            AgentWorkflowRunner(corpus=corpus, retrieval=RetrievalPipeline(HybridLiteRetriever(corpus)))
        )

    def test_service_returns_human_task_and_no_external_write(self) -> None:
        case = CaseContext(
            case_id="HITL-001",
            customer_id="SME-001",
            existing_customer=True,
            product=ProductType.WORKING_CAPITAL,
            requested_amount=2_000_000_000,
            submitted_documents=["BCTC"],
            required_documents=["BCTC", "TAX_DECLARATION"],
            annual_revenue=12_000_000_000,
            tax_declared_revenue=8_000_000_000,
            collateral_ratio=0.1,
            kyc_aml_flags=["AML_REVIEW"],
        )
        package = self.service.run_case(case)
        self.assertEqual("NEEDS_MORE_EVIDENCE", package.final_status)
        self.assertEqual("ESCALATE", package.critic_verdict)
        self.assertTrue(package.human_tasks)
        self.assertFalse(package.external_write_executed)
        self.assertTrue(all(action.requires_human_approval for action in package.proposed_actions))

    def test_rework_is_bounded(self) -> None:
        state = WorkflowState(case=CaseContext(
            case_id="REWORK-001",
            customer_id="SME-001",
            existing_customer=True,
            product=ProductType.CORPORATE_OVERDRAFT,
            requested_amount=100_000_000,
        ))
        from nexusops_agent.orchestration.rework import BoundedReworkController
        controller = BoundedReworkController()
        calls = []
        self.assertTrue(controller.apply_once(state, lambda: calls.append(1)))
        self.assertFalse(controller.apply_once(state, lambda: calls.append(2)))
        self.assertEqual([1], calls)


if __name__ == "__main__":
    unittest.main()
