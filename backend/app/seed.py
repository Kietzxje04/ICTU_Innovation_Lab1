from __future__ import annotations

import argparse
import random
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import CaseRecord


CASE_FIXTURES = [
    dict(
        case_id="toan-cau", customer_id="SME-TOAN-CAU", code="HS-2023-8901",
        name="Công ty TNHH Giải pháp Công nghệ Toàn cầu", short_name="Công nghệ Toàn cầu",
        owner="Marcus Chen", display_amount="$450,000", purpose="Vốn lưu động", sla="2h 15m",
        submitted_label="10:45 24/10", agent_label="AI-Agent-Alpha", score=82,
        display_status="Đang chờ rà soát", risk="Trung bình", issue="Chênh lệch thu nhập > 15%",
        existing_customer=True, product="WORKING_CAPITAL", requested_amount=450_000,
        relationship_months=30, submitted_documents=["BCTC", "KYC"],
        required_documents=["BCTC", "KYC", "TAX_DECLARATION_Q4"], annual_revenue=12_000_000_000,
        pretax_profit_last_2_years=[920_000_000, 1_050_000_000], tax_declared_revenue=10_000_000_000,
        cic_bad_debt=False, kyc_aml_flags=[], case_metadata={"currency": "USD", "source": "frontend-data.ts"},
    ),
    dict(
        case_id="hung-phat", customer_id="SME-HUNG-PHAT", code="HS-2023-8895",
        name="Công ty TNHH Hưng Phát", short_name="Hưng Phát", owner="Nguyễn Minh Anh",
        display_amount="₫8.2 tỷ", purpose="Mở rộng nhà xưởng", sla="45m", submitted_label="09:12 24/10",
        agent_label="AI-Agent-Beta", score=94, display_status="Chấp nhận", risk="Thấp",
        issue="Không có cảnh báo trọng yếu", existing_customer=True, product="WORKING_CAPITAL",
        requested_amount=8_200_000_000, relationship_months=54,
        submitted_documents=["BCTC", "KYC", "TAX_DECLARATION", "BUSINESS_LICENSE"],
        required_documents=["BCTC", "KYC", "TAX_DECLARATION", "BUSINESS_LICENSE"],
        annual_revenue=42_000_000_000, pretax_profit_last_2_years=[3_800_000_000, 4_200_000_000],
        tax_declared_revenue=41_500_000_000, cic_bad_debt=False, kyc_aml_flags=[],
        case_metadata={"currency": "VND", "source": "frontend-data.ts"},
    ),
    dict(
        case_id="sai-gon", customer_id="SME-SAI-GON", code="HS-2023-8872",
        name="Công ty Cổ phần Đầu tư Sài Gòn", short_name="Đầu tư Sài Gòn", owner="Lê Hoàng Nam",
        display_amount="₫15 tỷ", purpose="Bổ sung vốn dự án", sla="1h 30m", submitted_label="16:30 23/10",
        agent_label="AI-Agent-Alpha", score=68, display_status="Từ chối", risk="Cao",
        issue="Đòn bẩy tài chính vượt ngưỡng chính sách", existing_customer=True, product="WORKING_CAPITAL",
        requested_amount=15_000_000_000, relationship_months=18,
        submitted_documents=["BCTC", "KYC", "TAX_DECLARATION"],
        required_documents=["BCTC", "KYC", "TAX_DECLARATION"], annual_revenue=25_000_000_000,
        pretax_profit_last_2_years=[300_000_000, 250_000_000], tax_declared_revenue=24_500_000_000,
        cic_bad_debt=True, kyc_aml_flags=[], case_metadata={"currency": "VND", "source": "frontend-data.ts"},
    ),
    dict(
        case_id="le-gia", customer_id="SME-LE-GIA", code="HS-2023-8850",
        name="Doanh nghiệp tư nhân Lê Gia", short_name="DNTN Lê Gia", owner="Trần Thanh Hà",
        display_amount="₫3.6 tỷ", purpose="Mua sắm thiết bị", sla="3h 05m", submitted_label="14:15 23/10",
        agent_label="AI-Agent-Gamma", score=76, display_status="Đã xác minh", risk="Trung bình",
        issue="Thiếu báo cáo công nợ quý gần nhất", existing_customer=True, product="CORPORATE_OVERDRAFT",
        requested_amount=3_600_000_000, relationship_months=26,
        submitted_documents=["KYC", "BUSINESS_LICENSE"],
        required_documents=["KYC", "BUSINESS_LICENSE", "RECEIVABLES_REPORT_Q3"], annual_revenue=18_000_000_000,
        pretax_profit_last_2_years=[1_100_000_000, 1_250_000_000], tax_declared_revenue=None,
        cic_bad_debt=False, kyc_aml_flags=[], case_metadata={"currency": "VND", "source": "frontend-data.ts"},
    ),
    dict(
        case_id="CASE-WC-2026-0142", customer_id="CUS-001842", code="CASE-WC-2026-0142",
        name="Công ty TNHH Công nghệ Toàn Cầu", short_name="Công nghệ Toàn Cầu", owner="Nguyễn Minh Anh",
        display_amount="₫12,000,000,000", purpose="Vốn lưu động", sla="02:15:00", submitted_label="2026-07-18 03:45",
        agent_label="NexusOps-Agent", score=0, display_status="Đang chờ rà soát", risk="Trung bình",
        issue="Chênh lệch doanh thu tài chính và khai thuế", existing_customer=True, product="WORKING_CAPITAL",
        requested_amount=12_000_000_000, relationship_months=38,
        submitted_documents=["BUSINESS_REGISTRATION", "FINANCIAL_STATEMENTS_2Y", "CIC_REPORT", "WORKING_CAPITAL_PLAN"],
        required_documents=["BUSINESS_REGISTRATION", "FINANCIAL_STATEMENTS_2Y", "TAX_RETURNS_2Y", "CIC_REPORT", "WORKING_CAPITAL_PLAN"],
        annual_revenue=48_000_000_000, pretax_profit_last_2_years=[3_200_000_000, 3_850_000_000],
        tax_declared_revenue=39_500_000_000, cic_bad_debt=False, kyc_aml_flags=[],
        case_metadata={"industry": "Phan phoi thiet bi", "branch": "ICTU Thai Nguyen", "currency": "VND", "snapshot_date": "2026-07-18"},
    ),
    dict(
        case_id="CASE-OD-2026-0138", customer_id="CUS-001227", code="CASE-OD-2026-0138",
        name="Cong ty Co phan Bao bi Hung Phat", short_name="Bao bi Hung Phat", owner="Tran Hoang Nam",
        display_amount="₫5,500,000,000", purpose="Thau chi doanh nghiep", sla="00:45:00", submitted_label="2026-07-18 02:10",
        agent_label="NexusOps-Agent", score=0, display_status="Đang chờ rà soát", risk="Trung bình",
        issue="Vong quay tai khoan can giai trinh", existing_customer=True, product="CORPORATE_OVERDRAFT",
        requested_amount=5_500_000_000, relationship_months=64,
        submitted_documents=["BUSINESS_REGISTRATION", "BANK_STATEMENTS_12M", "CIC_REPORT", "LOAN_PURPOSE_PLAN"],
        required_documents=["BUSINESS_REGISTRATION", "BANK_STATEMENTS_12M", "CIC_REPORT", "LOAN_PURPOSE_PLAN"],
        annual_revenue=76_000_000_000, pretax_profit_last_2_years=[5_400_000_000, 6_100_000_000],
        tax_declared_revenue=74_800_000_000, cic_bad_debt=False, kyc_aml_flags=[],
        case_metadata={"industry": "San xuat bao bi", "branch": "ICTU Ha Noi", "currency": "VND", "turnover_alert": "true", "snapshot_date": "2026-07-18"},
    ),
    dict(
        case_id="CASE-WC-2026-0129", customer_id="CUS-004105", code="CASE-WC-2026-0129",
        name="Cong ty Co phan Xuat nhap khau Dong A", short_name="Xuat nhap khau Dong A", owner="Le Thu Ha",
        display_amount="₫18,000,000,000", purpose="Von luu dong", sla="02:15:00", submitted_label="2026-07-17 09:20",
        agent_label="NexusOps-Agent", score=0, display_status="Đang chờ rà soát", risk="Cao",
        issue="Can xac minh chu so huu huong loi", existing_customer=True, product="WORKING_CAPITAL",
        requested_amount=18_000_000_000, relationship_months=19,
        submitted_documents=["BUSINESS_REGISTRATION", "FINANCIAL_STATEMENTS_2Y", "TAX_RETURNS_2Y", "CIC_REPORT", "WORKING_CAPITAL_PLAN"],
        required_documents=["BUSINESS_REGISTRATION", "FINANCIAL_STATEMENTS_2Y", "TAX_RETURNS_2Y", "CIC_REPORT", "WORKING_CAPITAL_PLAN"],
        annual_revenue=91_000_000_000, pretax_profit_last_2_years=[2_100_000_000, 1_650_000_000],
        tax_declared_revenue=90_500_000_000, cic_bad_debt=False, kyc_aml_flags=["BENEFICIAL_OWNER_REVIEW"],
        case_metadata={"industry": "Xuat nhap khau", "branch": "ICTU Bac Ninh", "currency": "VND", "snapshot_date": "2026-07-17"},
    ),
    dict(
        case_id="CASE-OD-2026-0117", customer_id="CUS-003014", code="CASE-OD-2026-0117",
        name="Cong ty TNHH Van tai Minh Long", short_name="Van tai Minh Long", owner="Pham Duc Long",
        display_amount="₫3,200,000,000", purpose="Thau chi doanh nghiep", sla="Tam dung", submitted_label="2026-07-17 06:05",
        agent_label="NexusOps-Agent", score=0, display_status="Đang chờ rà soát", risk="Cao",
        issue="CIC co no xau va thieu ke hoach su dung von", existing_customer=True, product="CORPORATE_OVERDRAFT",
        requested_amount=3_200_000_000, relationship_months=11,
        submitted_documents=["BUSINESS_REGISTRATION", "BANK_STATEMENTS_12M", "CIC_REPORT"],
        required_documents=["BUSINESS_REGISTRATION", "BANK_STATEMENTS_12M", "CIC_REPORT", "LOAN_PURPOSE_PLAN"],
        annual_revenue=22_000_000_000, pretax_profit_last_2_years=[900_000_000, 720_000_000],
        tax_declared_revenue=21_700_000_000, cic_bad_debt=True, kyc_aml_flags=[],
        case_metadata={"industry": "Van tai", "branch": "ICTU Hai Phong", "currency": "VND", "snapshot_date": "2026-07-17"},
    ),
    dict(
        case_id="CASE-WC-2026-0104", customer_id="CUS-NEW-0088", code="CASE-WC-2026-0104",
        name="Cong ty TNHH Nong san An Phu", short_name="Nong san An Phu", owner="Do Khanh Linh",
        display_amount="₫7,500,000,000", purpose="Von luu dong", sla="Tam dung", submitted_label="2026-07-16 08:40",
        agent_label="NexusOps-Agent", score=0, display_status="Đang chờ rà soát", risk="Cao",
        issue="Khach hang moi, thieu ho so va co co AML", existing_customer=False, product="WORKING_CAPITAL",
        requested_amount=7_500_000_000, relationship_months=0,
        submitted_documents=["BUSINESS_REGISTRATION", "FINANCIAL_STATEMENTS_2Y", "WORKING_CAPITAL_PLAN"],
        required_documents=["BUSINESS_REGISTRATION", "FINANCIAL_STATEMENTS_2Y", "TAX_RETURNS_2Y", "CIC_REPORT", "WORKING_CAPITAL_PLAN"],
        annual_revenue=16_500_000_000, pretax_profit_last_2_years=[420_000_000, -180_000_000],
        tax_declared_revenue=14_200_000_000, cic_bad_debt=False, kyc_aml_flags=["NEW_CUSTOMER_KYC_PENDING"],
        case_metadata={"industry": "Thuong mai nong san", "branch": "ICTU Thai Nguyen", "currency": "VND", "snapshot_date": "2026-07-16"},
    ),
]


def seed_cases(session: Session) -> None:
    existing = {record.case_id: record for record in session.scalars(select(CaseRecord))}
    for fixture in CASE_FIXTURES:
        record = existing.get(fixture["case_id"])
        if record is None:
            session.add(CaseRecord(**fixture))
            continue
        for field, value in fixture.items():
            if field != "case_id":
                setattr(record, field, value)
    session.commit()


CANONICAL_WORKING_CAPITAL_DOCUMENTS = [
    "BUSINESS_REGISTRATION",
    "FINANCIAL_STATEMENTS_2Y",
    "TAX_RETURNS_2Y",
    "CIC_REPORT",
    "WORKING_CAPITAL_PLAN",
]
CANONICAL_OVERDRAFT_DOCUMENTS = [
    "BUSINESS_REGISTRATION",
    "BANK_STATEMENTS_12M",
    "FINANCIAL_STATEMENTS_2Y",
    "TAX_RETURNS_2Y",
    "CIC_REPORT",
    "OVERDRAFT_REQUEST",
]


def _mock_case(index: int, rng: random.Random, prefix: str = "MOCK") -> dict[str, object]:
    # Keep the large fixture set representative instead of relying on random
    # chance for rare branches. Every 12 records covers one business scenario.
    scenario = (index - 1) % 12
    product = "CORPORATE_OVERDRAFT" if index % 2 else "WORKING_CAPITAL"
    product_code = "OD" if product == "CORPORATE_OVERDRAFT" else "WC"
    case_id = f"{prefix}-{product_code}-{index:06d}"
    existing_customer = rng.random() >= 0.08
    relationship_months = rng.randint(12, 96) if existing_customer else 0
    annual_revenue = rng.randint(5, 200) * 1_000_000_000
    requested_amount = rng.randint(2, 40) * 100_000_000
    profit_1 = rng.randint(-2, 12) * 100_000_000
    profit_2 = rng.randint(-2, 15) * 100_000_000
    tax_declared_revenue = round(annual_revenue * rng.uniform(0.82, 1.03), 2)
    cic_bad_debt = rng.random() < 0.06
    aml_flags = ["BENEFICIAL_OWNER_REVIEW"] if rng.random() < 0.05 else []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if product == "CORPORATE_OVERDRAFT":
        required = list(CANONICAL_OVERDRAFT_DOCUMENTS)
        submitted = [item for item in required if rng.random() >= 0.18]
        turnover = annual_revenue * rng.uniform(0.45, 2.4)
        average_inflow = turnover / 12
        overdraft_purpose = rng.choice([
            "Bổ sung vốn lưu động qua tài khoản thanh toán",
            "Thanh toán nhà cung cấp ngắn hạn",
            "Bù đắp chênh lệch dòng tiền theo mùa vụ",
        ])
        stability = rng.uniform(0.35, 0.98)
        conduct_flags = ["IRREGULAR_CLEANUP"] if rng.random() < 0.04 else []
        purpose = "Thấu chi doanh nghiệp"
        issue = "Cần rà soát vòng quay tài khoản" if stability < 0.6 else "Readiness đang chờ rà soát"
        collateral_ratio = None
    else:
        required = list(CANONICAL_WORKING_CAPITAL_DOCUMENTS)
        submitted = [item for item in required if rng.random() >= 0.18]
        overdraft_purpose = None
        turnover = None
        average_inflow = None
        stability = None
        conduct_flags = []
        purpose = "Vốn lưu động"
        issue = "Chênh lệch doanh thu tài chính và khai thuế" if tax_declared_revenue / annual_revenue < 0.9 else "Readiness đang chờ rà soát"
        collateral_ratio = rng.uniform(0.05, 0.8)

    # Deterministic coverage matrix. Product-specific fields intentionally
    # remain null where the product does not use them.
    if scenario == 0:  # clean, complete PASS
        submitted = list(required)
        cic_bad_debt, aml_flags, conduct_flags = False, [], []
        tax_declared_revenue = annual_revenue
    elif scenario == 1:  # missing mandatory documents
        submitted = list(required[: max(1, len(required) // 2)])
    elif scenario == 2:  # material tax mismatch
        submitted = list(required)
        tax_declared_revenue = round(annual_revenue * 0.72, 2)
    elif scenario == 3:  # CIC bad debt
        submitted = list(required)
        cic_bad_debt = True
    elif scenario == 4:  # AML / beneficial-owner escalation
        submitted = list(required)
        aml_flags = ["BENEFICIAL_OWNER_REVIEW"]
    elif scenario == 5:  # new customer / KYC pending
        existing_customer, relationship_months = False, 0
        submitted = list(required[: max(1, len(required) - 2)])
        aml_flags = ["NEW_CUSTOMER_KYC_PENDING"]
    elif scenario == 6:  # loss-making business
        submitted = list(required)
        profit_1, profit_2 = -250_000_000, -600_000_000
    elif scenario == 7:  # account turnover unavailable (OD) / thin evidence (WC)
        submitted = list(required)
        if product == "CORPORATE_OVERDRAFT":
            turnover = average_inflow = stability = None
        else:
            tax_declared_revenue = None
    elif scenario == 8:  # irregular cleanup / conduct warning
        submitted = list(required)
        if product == "CORPORATE_OVERDRAFT":
            conduct_flags = ["IRREGULAR_CLEANUP"]
    elif scenario == 9:  # unstable turnover (OD) or high leverage (WC)
        submitted = list(required)
        if product == "CORPORATE_OVERDRAFT":
            stability = 0.38
        else:
            collateral_ratio = 0.08
    elif scenario == 10:  # complete but borderline relationship
        submitted = list(required)
        existing_customer, relationship_months = True, 12
    else:  # combined blockers to exercise mandatory critic and policy gate
        submitted = list(required[: max(1, len(required) - 1)])
        cic_bad_debt = True
        aml_flags = ["BENEFICIAL_OWNER_REVIEW"]
        tax_declared_revenue = round(annual_revenue * 0.78, 2)

    scenario_codes = [
        "CLEAN_COMPLETE", "MISSING_DOCUMENTS", "TAX_MISMATCH", "CIC_BAD_DEBT",
        "AML_REVIEW", "NEW_CUSTOMER_KYC", "NEGATIVE_PROFIT", "MISSING_CORE_EVIDENCE",
        "IRREGULAR_ACCOUNT_CONDUCT", "PRODUCT_RISK_METRIC", "BORDERLINE_RELATIONSHIP",
        "COMBINED_BLOCKERS",
    ]
    scenario_code = scenario_codes[scenario]
    issue = scenario_code.replace("_", " ").title()
    risk = "Cao" if cic_bad_debt or aml_flags or profit_2 < 0 else "Trung bình" if scenario != 0 else "Thấp"
    score = rng.randint(45, 96)
    return {
        "case_id": case_id,
        "customer_id": f"{prefix}-CUS-{index:06d}",
        "code": case_id,
        "name": f"Công ty Mock NexusOps {index:06d}",
        "short_name": f"NexusOps Mock {index:06d}",
        "owner": rng.choice(["Nguyễn Minh Anh", "Trần Hoàng Nam", "Lê Thu Hà", "Phạm Đức Long"]),
        "display_amount": f"₫{requested_amount:,.0f}",
        "purpose": purpose,
        "sla": rng.choice(["00:45:00", "01:30:00", "02:15:00", "03:00:00"]),
        "submitted_label": now,
        "agent_label": "NexusOps-Agent",
        "score": score,
        "display_status": "Đang chờ rà soát",
        "risk": risk,
        "issue": issue,
        "existing_customer": existing_customer,
        "product": product,
        "requested_amount": requested_amount,
        "relationship_months": relationship_months,
        "submitted_documents": submitted,
        "required_documents": required,
        "annual_revenue": annual_revenue,
        "pretax_profit_last_2_years": [profit_1, profit_2],
        "tax_declared_revenue": tax_declared_revenue,
        "collateral_ratio": collateral_ratio,
        "twelve_month_account_turnover": turnover,
        "account_history_months": relationship_months,
        "twelve_month_credit_turnover": turnover,
        "average_monthly_credit_inflow": average_inflow,
        "turnover_stability_ratio": stability,
        "expected_utilization_ratio": rng.uniform(0.35, 0.95) if product == "CORPORATE_OVERDRAFT" else None,
        "negative_balance_days": rng.randint(5, 80) if product == "CORPORATE_OVERDRAFT" else None,
        "cleanup_days": rng.randint(2, 20) if product == "CORPORATE_OVERDRAFT" else None,
        "overdraft_purpose": overdraft_purpose,
        "loan_purpose": "Bổ sung vốn lưu động phục vụ hoạt động kinh doanh" if product == "WORKING_CAPITAL" else None,
        "account_conduct_flags": conduct_flags,
        "cic_bad_debt": cic_bad_debt,
        "kyc_aml_flags": aml_flags,
        "case_metadata": {"source": "mock-seed", "currency": "VND", "generated_at": now, "scenario": scenario_code},
    }


def seed_mock_cases(session: Session, count: int = 1000, *, seed: int = 20260718, prefix: str = "MOCK", refresh: bool = False) -> tuple[int, int]:
    """Add deterministic synthetic cases; optionally refresh an existing mock cohort."""
    if count < 1:
        raise ValueError("count must be greater than zero")
    existing_ids = set(session.scalars(select(CaseRecord.case_id)))
    rng = random.Random(seed)
    records = []
    skipped = 0
    for index in range(1, count + 1):
        payload = _mock_case(index, rng, prefix)
        if payload["case_id"] in existing_ids:
            if refresh:
                record = session.scalar(select(CaseRecord).where(CaseRecord.case_id == payload["case_id"]))
                if record:
                    for field, value in payload.items():
                        setattr(record, field, value)
            else:
                skipped += 1
            continue
        records.append(CaseRecord(**payload))
    session.add_all(records)
    session.commit()
    return len(records), skipped


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed NexusOps demo/mock cases into PostgreSQL")
    parser.add_argument("--count", type=int, default=0, help="number of additional deterministic mock cases")
    parser.add_argument("--seed", type=int, default=20260718, help="random seed for repeatable data")
    parser.add_argument("--prefix", default="MOCK", help="case/customer ID prefix")
    parser.add_argument("--refresh", action="store_true", help="refresh existing records in this mock cohort")
    args = parser.parse_args()
    from .database import SessionLocal, create_schema

    create_schema()
    with SessionLocal() as session:
        seed_cases(session)
        if args.count:
            inserted, skipped = seed_mock_cases(session, args.count, seed=args.seed, prefix=args.prefix, refresh=args.refresh)
        else:
            inserted, skipped = 0, 0
    print(f"Seeded {len(CASE_FIXTURES)} demo cases; mock inserted={inserted}, skipped={skipped}")
