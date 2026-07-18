from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

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
    cic_bad_debt: bool | None = None
    kyc_aml_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)
