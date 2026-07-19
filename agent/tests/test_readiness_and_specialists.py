import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.agents.specialists import ComplianceAgent, CreditAgent, ProductAgent
from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.enums import ProductType
from nexusops_agent.contracts.state import WorkflowState
from nexusops_agent.nodes.readiness_rules import ReadinessRuleEngine
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.rag.retriever import HybridLiteRetriever


class ReadinessAndSpecialistsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        corpus = RagCorpus(ROOT / "final_rag_data_normalized_v1.json")
        cls.pipeline = RetrievalPipeline(HybridLiteRetriever(corpus))
        cls.rule_engine = ReadinessRuleEngine(ROOT / "configs" / "products")

    def overdraft_case(self) -> CaseContext:
        return CaseContext(
            case_id="OD-001",
            customer_id="SME-001",
            existing_customer=True,
            product=ProductType.CORPORATE_OVERDRAFT,
            requested_amount=500_000_000,
            relationship_months=18,
            submitted_documents=["BUSINESS_REGISTRATION", "BANK_STATEMENTS_12M", "FINANCIAL_STATEMENTS_2Y", "TAX_RETURNS_2Y", "CIC_REPORT", "OVERDRAFT_REQUEST"],
            annual_revenue=15_000_000_000,
            tax_declared_revenue=14_800_000_000,
            pretax_profit_last_2_years=[500_000_000, 650_000_000],
            turnover_stability_ratio=0.8,
            overdraft_purpose="Bổ sung vốn lưu động qua tài khoản thanh toán",
            twelve_month_credit_turnover=20_000_000_000,
            cic_bad_debt=False,
        )

    def test_overdraft_is_readiness_not_credit_approval(self) -> None:
        assessment = self.rule_engine.assess(self.overdraft_case())
        self.assertEqual("READY_FOR_HUMAN_REVIEW", assessment.status)
        self.assertIn("SYNTHETIC DEMO POLICY", assessment.warnings[0])
        artifact = CreditAgent(self.rule_engine).run(WorkflowState(case=self.overdraft_case()))
        self.assertEqual("PASS", artifact.status)
        self.assertIn("HUMAN_CREDIT_REVIEW", artifact.proposed_actions)

    def test_working_capital_tax_gap_requires_more_evidence(self) -> None:
        case = CaseContext(
            case_id="WC-001",
            customer_id="SME-002",
            existing_customer=True,
            product=ProductType.WORKING_CAPITAL,
            requested_amount=2_000_000_000,
            submitted_documents=["BCTC", "TAX_DECLARATION"],
            annual_revenue=12_000_000_000,
            tax_declared_revenue=9_000_000_000,
            collateral_ratio=0.25,
            metadata={"loan_purpose": "Bổ sung vốn lưu động"},
        )
        assessment = self.rule_engine.assess(case)
        self.assertEqual("NEEDS_MORE_EVIDENCE", assessment.status)
        failed = {result.reason_code for result in assessment.rule_results if result.status == "FAIL"}
        self.assertIn("FINANCIAL_TAX_MISMATCH", failed)

    def test_product_agent_uses_demo_namespace_with_disclaimer(self) -> None:
        artifact = ProductAgent(self.pipeline, demo_mode=True).run(WorkflowState(case=self.overdraft_case()))
        self.assertTrue(artifact.claims)
        self.assertEqual("PASS", artifact.status)
        self.assertEqual([], artifact.warnings)
        self.assertTrue(artifact.raw["demo_evidence_used"])
        self.assertIn("SYNTHETIC_DEMO_POLICY_NOT_OFFICIAL", artifact.raw["notices"])

    def test_compliance_skips_without_trigger(self) -> None:
        state = WorkflowState(case=self.overdraft_case())
        artifact = ComplianceAgent(self.pipeline).run(state)
        self.assertEqual("PASS", artifact.status)
        self.assertTrue(artifact.raw["retrieval_skipped"])


if __name__ == "__main__":
    unittest.main()
