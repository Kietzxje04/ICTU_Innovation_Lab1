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
]


def seed_cases(session: Session) -> None:
    if session.scalar(select(CaseRecord.case_id).limit(1)) is not None:
        return
    session.add_all(CaseRecord(**fixture) for fixture in CASE_FIXTURES)
    session.commit()
