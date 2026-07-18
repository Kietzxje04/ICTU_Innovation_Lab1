from __future__ import annotations

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
