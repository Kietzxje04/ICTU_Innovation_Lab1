# Phase 6 Review Checklist

- [x] Golden cases bao gồm auto-readiness, conflict/HITL và out-of-scope.
- [x] Evaluation đo final status, critic, route, mandatory tail và external write.
- [x] Backend handoff chỉ qua `AgentService` typed contract.
- [x] Secret scan được chạy trên toàn folder Agent.
- [x] Model IDs được đối chiếu với FPT `/v1/models`.
- [x] RAG source hash được kiểm tra sau mọi phase.
- [x] Không có live credit decision hoặc external write.

## Điều kiện trước khi bật provider live

1. Rotate key đã gửi trong hội thoại.
2. Tạo `agent/.env` cục bộ và đặt `FPT_AI_API_KEY` mới.
3. Không commit `.env`.
4. Chạy một smoke request không chứa PII.
5. Pin model registry version và lưu latency/token usage đã redaction.
