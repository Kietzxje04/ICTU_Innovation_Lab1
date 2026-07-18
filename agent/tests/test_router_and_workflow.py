import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.enums import ProductType
from nexusops_agent.orchestration.router import route_case
from nexusops_agent.orchestration.workflow import load_workflow


class RouterAndWorkflowTest(unittest.TestCase):
    def case(self, flags: list[str] | None = None) -> CaseContext:
        return CaseContext(
            case_id="C1",
            customer_id="SME1",
            existing_customer=True,
            product=ProductType.WORKING_CAPITAL,
            requested_amount=1_000_000_000,
            kyc_aml_flags=flags or [],
        )

    def test_compliance_is_sparse_routed(self) -> None:
        self.assertNotIn("COMPLIANCE_AGENT", route_case(self.case()).nodes)
        self.assertIn("COMPLIANCE_AGENT", route_case(self.case(["AML_FLAG"])).nodes)

    def test_mandatory_tail_is_locked(self) -> None:
        decision = route_case(self.case())
        self.assertEqual(["MANDATORY_CRITIC", "CITATION_VALIDATOR", "POLICY_GATE"], decision.nodes[-3:])
        for name in ("overdraft.json", "working_capital.json"):
            workflow = load_workflow(ROOT / "configs" / "workflows" / name)
            self.assertEqual(1, workflow.max_rework)


if __name__ == "__main__":
    unittest.main()
