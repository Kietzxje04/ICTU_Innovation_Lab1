# NexusOps AI - Agent Layer

## Live mode

Đặt `NEXUSOPS_AI_MODE=live` và `NEXUSOPS_DEMO_MODE=false`. Live runtime sử dụng FPT AI Factory cho Product/Credit/Compliance/Critic, FPT reranker cho RAG và giữ deterministic hard-rule fallback có ghi warning khi provider timeout. Fallback này không dùng dữ liệu mock.

```powershell
$env:NEXUSOPS_AI_MODE="live"
$env:NEXUSOPS_DEMO_MODE="false"
python scripts\live_fpt_smoke_test.py
```

Agent Layer cho hai workflow `CORPORATE_OVERDRAFT` và `WORKING_CAPITAL`.

## Trách nhiệm

- Agent là nguồn chuẩn cho product contract, document matrix, routing, metrics, RAG, Mandatory Critic và Citation Validator.
- Backend là lớp persistence/API/audit trên PostgreSQL.
- Frontend chỉ thu thập input và hiển thị readiness output; không tự quyết workflow hay policy.
- Kết quả chỉ là readiness cho Human-in-the-loop, không phải phê duyệt, từ chối, hạn mức hay lãi suất.

## Corporate Overdraft

Thấu chi doanh nghiệp là hạn mức quay vòng trên tài khoản thanh toán (`REVOLVING_LIMIT`), không phải khoản vay giải ngân một lần. Agent kiểm tra lịch sử tài khoản, doanh số ghi Có 12 tháng, dòng tiền bình quân tháng, độ ổn định, tỷ lệ hạn mức đề nghị/dòng tiền, hành vi cleanup, CIC/KYC/AML và đối chiếu tài chính-thuế.

Danh mục chuẩn:

```text
BUSINESS_REGISTRATION
BANK_STATEMENTS_12M
FINANCIAL_STATEMENTS_2Y
TAX_RETURNS_2Y
CIC_REPORT
OVERDRAFT_REQUEST
```

## Working Capital

Yêu cầu mục đích vay, tỷ lệ tài sản bảo đảm, báo cáo tài chính 2 năm, khai thuế 2 năm, CIC và kế hoạch vốn lưu động.

## Dữ liệu và cấu trúc

`final_rag_data_normalized_v1.json` là input read-only. Runtime index/trace/evaluation ghi vào `runtime/`. Các ngưỡng trong `configs/products/*.json` là `SYNTHETIC_DEMO_POLICY`, không phải chính sách chính thức.

```text
agent/
├── configs/                 # product, routing, workflow, model registry
├── src/nexusops_agent/
│   ├── agents/              # planner, specialists, mandatory critic
│   ├── contracts/           # typed CaseContext, artifacts, workflow state
│   ├── nodes/               # deterministic and RAG-backed nodes
│   ├── orchestration/       # router, workflow and bounded rework
│   ├── rag/                 # loader, retriever, citation validator
│   └── tools/               # allowlisted banking adapters
├── scripts/
├── tests/
└── runtime/
```

## Kiểm tra

```powershell
cd D:\D\abc
.\backend\.venv313\Scripts\python.exe -m unittest discover -s agent/tests -v
```

FPT AI Factory dùng OpenAI-compatible base URL. Chỉ đặt `FPT_AI_API_KEY` trong `.env` cục bộ; deterministic workflow không cần key.
