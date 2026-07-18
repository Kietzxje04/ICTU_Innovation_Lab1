from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.enums import ProductType
from nexusops_agent.workflows.runner import AgentWorkflowRunner


def main() -> None:
    case = CaseContext(
        case_id="DEMO-WC-001",
        customer_id="SME-001",
        existing_customer=True,
        product=ProductType.WORKING_CAPITAL,
        requested_amount=2_000_000_000,
        relationship_months=24,
        submitted_documents=["BCTC", "TAX_DECLARATION", "CIC_CONSENT", "WORKING_CAPITAL_PLAN"],
        annual_revenue=12_000_000_000,
        tax_declared_revenue=9_500_000_000,
        collateral_ratio=0.25,
        cic_bad_debt=False,
        kyc_aml_flags=["REVIEW_BENEFICIAL_OWNER"],
        metadata={"loan_purpose": "Bổ sung vốn lưu động"},
    )
    state = AgentWorkflowRunner().run(case)
    print(json.dumps(state.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
