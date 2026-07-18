# Phase 4 Review Checklist

- [x] Hai workflow dùng chung typed `WorkflowState`.
- [x] Dynamic sparse route theo product, missing data và KYC/AML trigger.
- [x] Mandatory tail luôn là Critic → Citation Validator → Policy Gate.
- [x] Sequential runner là deterministic fallback/test baseline.
- [x] LangGraph adapter compile case-specific StateGraph khi dependency được cài.
- [x] Node trace có case/node/status/engine/input-output summary.
- [x] Overdraft không gọi Compliance nếu không có trigger.
- [x] Working Capital conflict trả `NEEDS_MORE_EVIDENCE`.

## Chưa đóng ở Phase 4

- Bounded rework và Human checkpoint được hoàn thiện ở Phase 5.
- LangGraph optional dependency chưa bắt buộc trong test environment; runner contracts đã tương thích.
