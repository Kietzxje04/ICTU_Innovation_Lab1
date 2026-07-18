# NexusOps AI — Agent Layer

Agent Layer cho `NexusOps AI V3.1 – Visual Hybrid-Agent Studio for SME Loan Readiness`.

## Phạm vi

- Hai workflow: Corporate Overdraft và Working Capital.
- Hybrid agents: deterministic nodes, local-LLM adapters và cloud-LLM adapters.
- Planner/router chỉ gọi specialist cần thiết.
- Mandatory Critic luôn chạy trước kết quả cuối.
- RAG tách namespace AML, Lending, Demo Policy và Quarantine.
- Citation Validator kiểm exact quote, content hash, authority, quality và validity.
- Không phê duyệt/từ chối khoản vay; chỉ tạo readiness artifacts và đề xuất HITL.

## Dữ liệu bất biến

`final_rag_data_normalized_v1.json` là input read-only. Code trong package chỉ đọc file này; index/runtime artifacts phải ghi vào `runtime/`.

## Cấu trúc

```text
agent/
├── final_rag_data_normalized_v1.json   # immutable input
├── configs/                            # model, routing, workflow definitions
├── prompts/                            # versioned prompts; không yêu cầu chain-of-thought
├── src/nexusops_agent/
│   ├── agents/                         # planner/specialists/mandatory critic
│   ├── contracts/                      # typed I/O artifacts và workflow state
│   ├── nodes/                          # deterministic và LLM node adapters
│   ├── orchestration/                  # engine registry, router, workflow compiler
│   ├── rag/                            # loader, namespace router, retriever, validator
│   ├── tools/                          # allowlisted banking tool adapters
│   └── observability/                  # node run events/traces
├── scripts/                            # validation và smoke test
├── tests/                              # unit tests
└── runtime/                            # generated indexes/traces; không commit payload
```

## Chạy kiểm tra

```powershell
cd E:\Downloads\Ddc\agent
python scripts\validate_rag_data.py
python scripts\smoke_test.py
python -m unittest discover -s tests -v
```

## Kết nối với Backend

Backend chỉ gọi Agent Layer qua một service adapter, truyền `CaseContext` và nhận `WorkflowState`/`AgentArtifact`. Browser không gọi trực tiếp model, vector store hoặc tool.

```text
React → FastAPI Backend → AgentService → Router/Workflow
                                      → Specialist/Deterministic Nodes
                                      → RAG/Tools
                                      → Mandatory Critic
                                      → Citation Validator
                                      → Readiness Artifact
```
