from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import ProductType


class CaseContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    customer_id: str
    existing_customer: bool
    product: ProductType
    requested_amount: float = Field(gt=0)
    relationship_months: int = Field(default=0, ge=0)
    submitted_documents: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    annual_revenue: float | None = Field(default=None, ge=0)
    pretax_profit_last_2_years: list[float] = Field(default_factory=list)
    tax_declared_revenue: float | None = Field(default=None, ge=0)
    current_assets: float | None = Field(default=None, ge=0)
    current_liabilities: float | None = Field(default=None, ge=0)
    total_debt: float | None = Field(default=None, ge=0)
    total_assets: float | None = Field(default=None, ge=0)
    operating_cash_flow: float | None = None
    annual_debt_service: float | None = Field(default=None, ge=0)
    collateral_ratio: float | None = Field(default=None, ge=0)
    twelve_month_account_turnover: float | None = Field(default=None, ge=0)
    # Corporate overdraft operating-account signals. These are readiness inputs,
    # never a credit limit/price approval.
    account_history_months: int | None = Field(default=None, ge=0)
    twelve_month_credit_turnover: float | None = Field(default=None, ge=0)
    average_monthly_credit_inflow: float | None = Field(default=None, ge=0)
    turnover_stability_ratio: float | None = Field(default=None, ge=0)
    expected_utilization_ratio: float | None = Field(default=None, ge=0, le=1)
    negative_balance_days: int | None = Field(default=None, ge=0)
    cleanup_days: int | None = Field(default=None, ge=0)
    overdraft_purpose: str | None = None
    account_conduct_flags: list[str] = Field(default_factory=list)
    loan_purpose: str | None = None
    cic_bad_debt: bool | None = None
    kyc_aml_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, values):
        if not isinstance(values, dict):
            return values
        values = dict(values)
        aliases = {
            "BCTC": "FINANCIAL_STATEMENTS_2Y",
            "TAX_DECLARATION": "TAX_RETURNS_2Y",
            "TAX_DECLARATION_Q4": "TAX_RETURNS_2Y",
            "CIC_CONSENT": "CIC_REPORT",
            "BUSINESS_LICENSE": "BUSINESS_REGISTRATION",
            "LOAN_PURPOSE_PLAN": "OVERDRAFT_REQUEST",
        }
        for field in ("submitted_documents", "required_documents"):
            documents = values.get(field)
            if isinstance(documents, list):
                values[field] = list(dict.fromkeys(aliases.get(str(item), str(item)) for item in documents))
        metadata = dict(values.get("metadata") or {})
        if values.get("loan_purpose") is None and metadata.get("loan_purpose"):
            values["loan_purpose"] = metadata["loan_purpose"]
        if values.get("overdraft_purpose") is None and metadata.get("overdraft_purpose"):
            values["overdraft_purpose"] = metadata["overdraft_purpose"]
        if values.get("twelve_month_credit_turnover") is None and values.get("twelve_month_account_turnover") is not None:
            values["twelve_month_credit_turnover"] = values["twelve_month_account_turnover"]
        if values.get("account_history_months") is None and values.get("relationship_months") is not None:
            values["account_history_months"] = values["relationship_months"]
        return values
