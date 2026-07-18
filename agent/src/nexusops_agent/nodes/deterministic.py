from __future__ import annotations

from nexusops_agent.contracts.case import CaseContext


def existing_customer_gate(case: CaseContext) -> tuple[bool, str]:
    return (case.existing_customer, "EXISTING_CUSTOMER" if case.existing_customer else "NEW_TO_BANK_OUT_OF_SCOPE")


def document_completeness(case: CaseContext) -> dict[str, object]:
    required = set(case.required_documents)
    submitted = set(case.submitted_documents)
    missing = sorted(required - submitted)
    ratio = 1.0 if not required else len(required & submitted) / len(required)
    return {"ratio": round(ratio, 4), "missing": missing, "complete": not missing}


def financial_tax_gap(case: CaseContext) -> float | None:
    if not case.annual_revenue or case.tax_declared_revenue is None:
        return None
    return abs(case.annual_revenue - case.tax_declared_revenue) / case.annual_revenue


def hardness_score(case: CaseContext) -> int:
    score = 0
    if not document_completeness(case)["complete"]:
        score += 1
    gap = financial_tax_gap(case)
    if gap is not None and gap > 0.10:
        score += 2
    if case.kyc_aml_flags:
        score += 2
    if case.cic_bad_debt:
        score += 2
    return score
