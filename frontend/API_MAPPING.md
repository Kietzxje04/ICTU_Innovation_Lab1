# Frontend ↔ Backend mapping sau khi API ổn định

Frontend hiện dùng `mockCases` qua `ReadinessAdapter`. Khi merge AgentService vào FastAPI,
thay implementation adapter, giữ nguyên page/component.

| Frontend | Agent contract | Ghi chú |
| --- | --- | --- |
| `ReadinessCase.context` | `CaseContext` | Giữ snake_case để serialize trực tiếp |
| `ReadinessCase.workflow.route` | `WorkflowState.route` | Route đã bao gồm mandatory tail |
| `workflow.artifacts[node]` | `WorkflowState.artifacts` | Hiển thị `status`, `summary`, `metrics`, `warnings`, `proposed_actions` |
| `workflow.critic_verdict` | `WorkflowState.critic_verdict` | `PENDING/PASS/REVISE/ESCALATE` |
| `workflow.final_status` | `WorkflowState.final_status` | Không map thành approve/reject |
| `evidence[]` | `EvidenceChunk` + `ValidationResult` | UI chỉ render citation và quality/provenance cần thiết |
| `workflow.trace[]` | runtime observability events | Có thể stream/poll sau, hiện mock snapshot |

Đề xuất endpoint khi backend hoàn thiện:

- `GET /api/v1/readiness/cases`
- `GET /api/v1/readiness/cases/{case_id}`
- `POST /api/v1/readiness/cases` (tạo `CaseContext`)
- `POST /api/v1/readiness/cases/{case_id}/handoff` (HITL handoff, không phải quyết định khoản vay)
- `GET /api/v1/readiness/cases/{case_id}/trace`

