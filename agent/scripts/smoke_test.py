from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.config import Settings
from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.enums import ProductType
from nexusops_agent.orchestration.router import route_case
from nexusops_agent.orchestration.workflow import load_workflow
from nexusops_agent.rag.loader import RagCorpus


def main() -> None:
    settings = Settings.from_env()
    corpus = RagCorpus(settings.rag_data_path)
    inventory = corpus.inventory()
    case = CaseContext(
        case_id="CASE-SMOKE-001",
        customer_id="SME-001",
        existing_customer=True,
        product=ProductType.WORKING_CAPITAL,
        requested_amount=2_000_000_000,
        submitted_documents=["BCTC"],
        required_documents=["BCTC", "TAX_DECLARATION"],
        annual_revenue=12_000_000_000,
        tax_declared_revenue=10_000_000_000,
        cic_bad_debt=False,
        kyc_aml_flags=["REVIEW_BENEFICIAL_OWNER"],
    )
    route = route_case(case)
    workflow = load_workflow(settings.config_dir / "workflows" / "working_capital.json")
    assert route.nodes[-4:] == ["MANDATORY_CRITIC", "CITATION_VALIDATOR", "READINESS_RULE_ENGINE", "POLICY_GATE"]
    print(json.dumps({"inventory": inventory, "route": route.model_dump(), "workflow": workflow.model_dump()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
