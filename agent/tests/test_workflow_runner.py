import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.enums import ProductType
from nexusops_agent.nodes.readiness_rules import ReadinessRuleEngine
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.rag.retriever import HybridLiteRetriever
from nexusops_agent.workflows.runner import AgentWorkflowRunner


class WorkflowRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        corpus = RagCorpus(ROOT / "final_rag_data_normalized_v1.json")
        cls.runner = AgentWorkflowRunner(
            corpus=corpus,
            retrieval=RetrievalPipeline(HybridLiteRetriever(corpus)),
            rule_engine=ReadinessRuleEngine(ROOT / "configs" / "products"),
        )

    def test_overdraft_sparse_route_and_mandatory_tail(self) -> None:
        case = CaseContext(
            case_id="OD-GRAPH-001",
            customer_id="SME-001",
            existing_customer=True,
            product=ProductType.CORPORATE_OVERDRAFT,
            requested_amount=500_000_000,
            relationship_months=18,
            submitted_documents=["BUSINESS_REGISTRATION", "BANK_STATEMENTS_12M", "FINANCIAL_STATEMENTS_2Y", "TAX_RETURNS_2Y", "CIC_REPORT", "OVERDRAFT_REQUEST"],
            annual_revenue=15_000_000_000,
            tax_declared_revenue=14_800_000_000,
            pretax_profit_last_2_years=[500_000_000, 650_000_000],
            twelve_month_account_turnover=20_000_000_000,
            turnover_stability_ratio=0.8,
            overdraft_purpose="Bổ sung vốn lưu động qua tài khoản thanh toán",
            cic_bad_debt=False,
        )
        state = self.runner.run(case)
        self.assertNotIn("COMPLIANCE_AGENT", state.route)
        self.assertEqual(["MANDATORY_CRITIC", "CITATION_VALIDATOR", "READINESS_RULE_ENGINE", "POLICY_GATE"], state.route[-4:])
        self.assertEqual("READY_FOR_HUMAN_REVIEW", state.final_status)
        self.assertEqual("PASS", state.critic_verdict)
        self.assertTrue(state.trace)

    def test_working_capital_conflict_routes_compliance_and_hitl(self) -> None:
        case = CaseContext(
            case_id="WC-GRAPH-001",
            customer_id="SME-002",
            existing_customer=True,
            product=ProductType.WORKING_CAPITAL,
            requested_amount=2_000_000_000,
            submitted_documents=["BCTC", "TAX_DECLARATION"],
            annual_revenue=12_000_000_000,
            tax_declared_revenue=8_000_000_000,
            collateral_ratio=0.1,
            kyc_aml_flags=["AML_REVIEW"],
            metadata={"loan_purpose": "Bổ sung vốn lưu động"},
        )
        state = self.runner.run(case)
        self.assertIn("COMPLIANCE_AGENT", state.route)
        self.assertEqual("REVISE", state.critic_verdict)
        self.assertEqual("NEEDS_MORE_EVIDENCE", state.final_status)
        self.assertIn("CITATION_VALIDATOR", state.artifacts)
        self.assertIn("POLICY_GATE", state.artifacts)


if __name__ == "__main__":
    unittest.main()
