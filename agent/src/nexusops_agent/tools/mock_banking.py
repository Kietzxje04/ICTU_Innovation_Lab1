from __future__ import annotations


def get_customer_snapshot(customer_id: str) -> dict[str, object]:
    return {"customer_id": customer_id, "existing_customer": True, "source": "MOCK_CUSTOMER_API"}


def get_cic_snapshot(customer_id: str) -> dict[str, object]:
    return {"customer_id": customer_id, "bad_debt": False, "source": "MOCK_CIC_API"}


def get_kyc_aml_snapshot(customer_id: str) -> dict[str, object]:
    return {"customer_id": customer_id, "flags": [], "source": "MOCK_KYC_AML_API"}


def get_account_turnover(customer_id: str) -> dict[str, object]:
    return {"customer_id": customer_id, "twelve_month_turnover": 12_000_000_000, "source": "MOCK_ACCOUNT_API"}
