from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexusops_agent.config import Settings
from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.decisions import ReadinessAssessment, RuleResult

from .deterministic import document_completeness, financial_tax_gap


def financial_metrics(case: CaseContext) -> dict[str, float]:
    metrics: dict[str, float] = {}
    if case.current_assets is not None and case.current_liabilities:
        metrics["current_ratio"] = case.current_assets / case.current_liabilities
    if case.total_debt is not None and case.total_assets:
        metrics["debt_to_assets"] = case.total_debt / case.total_assets
    if case.operating_cash_flow is not None and case.annual_debt_service:
        metrics["dscr_proxy"] = case.operating_cash_flow / case.annual_debt_service
    turnover = case.twelve_month_credit_turnover or case.twelve_month_account_turnover
    average_inflow = case.average_monthly_credit_inflow
    if average_inflow is None and turnover is not None:
        average_inflow = turnover / 12
    if turnover is not None:
        metrics["twelve_month_credit_turnover"] = turnover
    if average_inflow is not None:
        metrics["average_monthly_credit_inflow"] = average_inflow
        if average_inflow > 0:
            metrics["requested_limit_to_monthly_inflow"] = case.requested_amount / average_inflow
    if case.turnover_stability_ratio is not None:
        metrics["turnover_stability_ratio"] = case.turnover_stability_ratio
    if case.expected_utilization_ratio is not None:
        metrics["expected_utilization_ratio"] = case.expected_utilization_ratio
    if case.negative_balance_days is not None:
        metrics["negative_balance_days"] = float(case.negative_balance_days)
    if case.cleanup_days is not None:
        metrics["cleanup_days"] = float(case.cleanup_days)
    gap = financial_tax_gap(case)
    if gap is not None:
        metrics["tax_revenue_gap"] = gap
    return {name: round(value, 6) for name, value in metrics.items()}


def _field_value(case: CaseContext, field: str, metrics: dict[str, float]) -> Any:
    if field in metrics:
        return metrics[field]
    if field.startswith("metadata."):
        return case.metadata.get(field.split(".", 1)[1])
    return getattr(case, field, None)


def _evaluate(actual: Any, operator: str, expected: Any) -> bool | None:
    if operator == "non_empty":
        return bool(str(actual).strip()) if actual is not None else None
    if operator == "all_gt":
        if not isinstance(actual, list) or len(actual) < 2:
            return None
        return all(value > expected for value in actual[-2:])
    if operator == "empty":
        if actual is None:
            return None
        return not bool(actual)
    if actual is None:
        return None
    if operator == ">=":
        return actual >= expected
    if operator == ">":
        return actual > expected
    if operator == "<=":
        return actual <= expected
    if operator == "==":
        return actual == expected
    raise ValueError(f"Unsupported operator: {operator}")


class ReadinessRuleEngine:
    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or Settings.from_env().config_dir / "products"

    def _load_pack(self, case: CaseContext) -> dict[str, Any]:
        filename = "corporate_overdraft.json" if case.product == "CORPORATE_OVERDRAFT" else "working_capital.json"
        return json.loads((self.config_dir / filename).read_text(encoding="utf-8"))

    def product_definition(self, product: str) -> dict[str, Any]:
        filename = "corporate_overdraft.json" if product == "CORPORATE_OVERDRAFT" else "working_capital.json"
        return json.loads((self.config_dir / filename).read_text(encoding="utf-8"))

    def canonical_case(self, case: CaseContext) -> CaseContext:
        pack = self._load_pack(case)
        return case.model_copy(update={"required_documents": list(pack["required_documents"])})

    def assess(self, case: CaseContext) -> ReadinessAssessment:
        if not case.existing_customer:
            return ReadinessAssessment(
                product=str(case.product),
                status="BLOCKED_OUT_OF_SCOPE",
                warnings=["NEW_TO_BANK_OUT_OF_MVP_SCOPE"],
            )
        pack = self._load_pack(case)
        case_for_docs = self.canonical_case(case)
        metrics = financial_metrics(case_for_docs)
        completeness = document_completeness(case_for_docs)
        results: list[RuleResult] = []
        for rule in pack["rules"]:
            actual = _field_value(case_for_docs, rule["field"], metrics)
            outcome = _evaluate(actual, rule["operator"], rule["value"])
            status = "UNKNOWN" if outcome is None else "PASS" if outcome else "FAIL"
            results.append(
                RuleResult(
                    rule_id=rule["rule_id"],
                    status=status,
                    actual=actual,
                    expected=f"{rule['operator']} {rule['value']}",
                    reason_code=rule["reason_code"],
                    source="SYNTHETIC_DEMO_POLICY",
                )
            )
        has_gap = bool(completeness["missing"]) or any(result.status in {"FAIL", "UNKNOWN"} for result in results)
        return ReadinessAssessment(
            product=str(case.product),
            status="NEEDS_MORE_EVIDENCE" if has_gap else "READY_FOR_HUMAN_REVIEW",
            rule_results=results,
            metrics=metrics,
            missing_documents=list(completeness["missing"]),
            warnings=["SYNTHETIC DEMO POLICY – NOT OFFICIAL SHB POLICY"],
        )
