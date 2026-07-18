from __future__ import annotations

from pydantic import BaseModel, Field

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.enums import ProductType


class RouteDecision(BaseModel):
    hardness: int = Field(ge=0)
    nodes: list[str]
    reasons: list[str]


def route_case(case: CaseContext) -> RouteDecision:
    nodes = ["EXISTING_CUSTOMER_GATE", "PRODUCT_AGENT", "DOCUMENT_COMPLETENESS"]
    reasons: list[str] = []
    hardness = 0

    if case.product == ProductType.CORPORATE_OVERDRAFT:
        nodes.extend(["ACCOUNT_TURNOVER", "CREDIT_AGENT"])
    else:
        nodes.extend(["FINANCIAL_METRICS", "TAX_CONSISTENCY", "CREDIT_AGENT"])

    missing = set(case.required_documents) - set(case.submitted_documents)
    if missing:
        hardness += 1
        reasons.append("MISSING_DOCUMENTS")
    if case.tax_declared_revenue is not None and case.annual_revenue:
        gap = abs(case.annual_revenue - case.tax_declared_revenue) / case.annual_revenue
        if gap > 0.10:
            hardness += 2
            reasons.append("FINANCIAL_TAX_MISMATCH")
    if case.kyc_aml_flags:
        hardness += 2
        nodes.append("COMPLIANCE_AGENT")
        reasons.append("KYC_AML_TRIGGER")
    if case.cic_bad_debt:
        hardness += 2
        reasons.append("CIC_BAD_DEBT")

    nodes.extend(["READINESS_RULE_ENGINE", "MANDATORY_CRITIC", "CITATION_VALIDATOR", "POLICY_GATE"])
    return RouteDecision(hardness=hardness, nodes=list(dict.fromkeys(nodes)), reasons=reasons)
