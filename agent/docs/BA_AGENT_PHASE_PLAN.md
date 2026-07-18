# NexusOps AI Agent Layer — Phase Plan

## Mục tiêu Agent Layer

Agent Layer nhận `CaseContext`, lập route có kiểm soát, gọi specialist theo hardness/trigger, truy vấn evidence đúng namespace, chạy Mandatory Critic và trả `WorkflowState` có citation, warnings, HITL route và audit trace.

Agent Layer không làm:

- Phê duyệt hoặc từ chối tín dụng cuối cùng.
- Sửa dữ liệu hồ sơ/khách hàng.
- Cho LLM gọi database/API tùy ý.
- Dùng AML regulation để suy ra credit eligibility.
- Ghi API key vào source, trace hoặc payload log.

## Phase 1 — BA contracts, model strategy và security baseline

Đầu ra:

- `CaseContext`, `WorkflowState`, `AgentArtifact`, `EvidenceChunk`, `CitationClaim`.
- Model registry theo role, engine và fallback.
- FPT AI Factory OpenAI-compatible provider adapter.
- `.env.example` không chứa secret; `.gitignore` chặn `.env`.
- Unit test contract/provider redaction/model diversity.

Exit gate:

- Không có key trong repository.
- Critic model khác family với Credit model.
- Model IDs thuộc allowlist của cuộc thi.

## Phase 2 — RAG ingestion/index abstraction

Đầu ra:

- Read-only loader cho `final_rag_data_normalized_v1.json`.
- Namespace router: `legal_aml`, `legal_lending`, `demo_internal_policy`, `quarantine`.
- Embedding adapter: Vietnamese_Embedding, fallback multilingual-e5-large.
- Reranker adapter: bge-reranker-v2-m3.
- Citation Validator: exact quote/hash/authority/quality/validity.

Exit gate:

- Billing text không còn.
- Không duplicate chunk/hash.
- `REVIEW_REQUIRED` không được searchable mặc định.
- Synthetic chunk luôn có disclaimer.

## Phase 3 — Deterministic nodes và specialists

Đầu ra:

- Existing Customer Gate.
- Document Completeness.
- Financial Metrics/Tax Consistency.
- Product, Credit, Compliance specialist contracts.
- Allowlisted mock tools: customer, account turnover, CIC, KYC/AML.

Exit gate:

- Formula/rule có test fixture.
- Agent không tự sửa input.
- Compliance chỉ route khi có trigger.

## Phase 4 — Orchestration cho hai workflow

Đầu ra:

- LangGraph StateGraph adapter.
- Overdraft auto-readiness path.
- Working Capital conflict/HITL path.
- Max one bounded rework.

Exit gate:

- Workflow publish thiếu Critic/Citation Validator/Policy Gate bị reject.
- Node I/O typed và trace được.

## Phase 5 — Mandatory Critic, HITL và AgentService

Đầu ra:

- Critic PASS/REVISE/ESCALATE.
- Evidence conflict detector.
- Human approval boundary.
- `AgentService.run_case()` adapter cho FastAPI backend.

Exit gate:

- Unsupported claim bị bắt.
- Không có hard action nếu chưa qua Policy Gate/approval.

## Phase 6 — Evaluation và demo readiness

Đầu ra:

- Golden queries/cases.
- Single-agent vs sparse multi-agent benchmark.
- Citation accuracy, abstention, latency, token/cost, route correctness.
- Prompt injection, stale data, wrong namespace, provider failure tests.

Exit gate:

- Không còn P0/P1 defect.
- Demo trace hiển thị input/output từng node.
- Backend chỉ dùng interface typed của Agent Layer.
