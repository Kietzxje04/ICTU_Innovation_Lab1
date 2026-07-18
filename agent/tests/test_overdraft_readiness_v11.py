import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.nodes.readiness_rules import ReadinessRuleEngine
from nexusops_agent.orchestration.router import route_case


DOCS = [
    "BUSINESS_REGISTRATION",
    "BANK_STATEMENTS_12M",
    "FINANCIAL_STATEMENTS_2Y",
    "TAX_RETURNS_2Y",
    "CIC_REPORT",
    "OVERDRAFT_REQUEST",
]


class CorporateOverdraftReadinessV11Test(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ReadinessRuleEngine(ROOT / "configs" / "products")

    def case(self, **updates) -> CaseContext:
        payload = {
            "case_id": "OD-V11",
            "customer_id": "SME-V11",
            "existing_customer": True,
            "product": "CORPORATE_OVERDRAFT",
            "requested_amount": 1_000_000_000,
            "relationship_months": 24,
            "submitted_documents": DOCS,
            "annual_revenue": 30_000_000_000,
            "pretax_profit_last_2_years": [1_000_000_000, 1_200_000_000],
            "tax_declared_revenue": 29_000_000_000,
            "twelve_month_credit_turnover": 24_000_000_000,
            "turnover_stability_ratio": 0.8,
            "overdraft_purpose": "Bổ sung vốn lưu động qua tài khoản thanh toán",
            "cic_bad_debt": False,
        }
        payload.update(updates)
        return CaseContext.model_validate(payload)

    def reason_statuses(self, case: CaseContext) -> dict[str, str]:
        result = self.engine.assess(case)
        return {item.reason_code: item.status for item in result.rule_results}

    def test_complete_overdraft_is_ready_for_human_review(self) -> None:
        self.assertEqual("READY_FOR_HUMAN_REVIEW", self.engine.assess(self.case()).status)

    def test_missing_bank_statements_is_document_gap(self) -> None:
        result = self.engine.assess(self.case(submitted_documents=[item for item in DOCS if item != "BANK_STATEMENTS_12M"]))
        self.assertIn("BANK_STATEMENTS_12M", result.missing_documents)

    def test_missing_turnover_is_unknown(self) -> None:
        statuses = self.reason_statuses(self.case(twelve_month_credit_turnover=None, twelve_month_account_turnover=None))
        self.assertEqual("UNKNOWN", statuses["ACCOUNT_TURNOVER_MISSING"])

    def test_unstable_turnover_is_flagged(self) -> None:
        self.assertEqual("FAIL", self.reason_statuses(self.case(turnover_stability_ratio=0.4))["TURNOVER_UNSTABLE"])

    def test_requested_limit_relative_to_inflow_is_flagged(self) -> None:
        case = self.case(requested_amount=5_000_000_000, average_monthly_credit_inflow=1_000_000_000)
        self.assertEqual("FAIL", self.reason_statuses(case)["REQUESTED_LIMIT_EXCESSIVE"])

    def test_cic_and_account_conduct_are_flagged(self) -> None:
        statuses = self.reason_statuses(self.case(cic_bad_debt=True, account_conduct_flags=["IRREGULAR_CLEANUP"]))
        self.assertEqual("FAIL", statuses["CIC_BAD_DEBT"])
        self.assertEqual("FAIL", statuses["ACCOUNT_CONDUCT_EXCEPTION"])

    def test_aml_trigger_routes_compliance(self) -> None:
        route = route_case(self.case(kyc_aml_flags=["BENEFICIAL_OWNER_REVIEW"]))
        self.assertIn("COMPLIANCE_AGENT", route.nodes)
        self.assertIn("KYC_AML_TRIGGER", route.reasons)

    def test_tax_mismatch_and_new_to_bank_are_not_ready(self) -> None:
        mismatch = self.engine.assess(self.case(tax_declared_revenue=20_000_000_000))
        self.assertEqual("NEEDS_MORE_EVIDENCE", mismatch.status)
        new_to_bank = self.engine.assess(self.case(existing_customer=False))
        self.assertEqual("BLOCKED_OUT_OF_SCOPE", new_to_bank.status)


if __name__ == "__main__":
    unittest.main()
