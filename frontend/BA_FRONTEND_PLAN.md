# NexusOps AI — Frontend delivery plan

Nguồn yêu cầu: `agent/README.md`, `agent/configs/workflows/*.json` và các contract trong
`agent/src/nexusops_agent/contracts/`.

## Nguyên tắc phạm vi

- Frontend chỉ thể hiện mức độ sẵn sàng của hồ sơ, bằng chứng, cảnh báo và đề xuất HITL.
- Không hiển thị hành động phê duyệt hoặc từ chối khoản vay.
- Browser không gọi trực tiếp LLM, RAG, vector store hoặc banking tools.
- Dữ liệu mock bám sát `CaseContext`, `WorkflowState`, `AgentArtifact`, `EvidenceChunk`.
- Tầng dữ liệu tách riêng để có thể đổi mock adapter sang backend adapter sau khi API ổn định.

## Phase 1 — Contract và information architecture

- Chuẩn hóa type TypeScript tương ứng contract Agent Layer.
- Mapping hai workflow và điều kiện route động (`KYC_AML_TRIGGER`, thiếu tài liệu, lệch thuế, CIC).
- Điều chỉnh ngôn ngữ UI từ quyết định tín dụng sang loan readiness.

Review gate: đủ trường `CaseContext`; đủ bốn trạng thái cuối; bắt buộc hiển thị Critic,
Citation Validator và Policy Gate.

## Phase 2 — Mock domain và data adapter

- Tạo hồ sơ mẫu cho cả Corporate Overdraft và Working Capital.
- Bao phủ các trạng thái: sẵn sàng rà soát, cần thêm bằng chứng, bị chặn và đang xử lý.
- Store hỗ trợ tạo hồ sơ mới và mô phỏng chạy workflow.

Review gate: component không phụ thuộc trực tiếp cấu trúc response backend; mock có thể thay
bằng API adapter mà không đổi page.

## Phase 3 — Dashboard và intake workflow

- Dashboard readiness, bộ lọc sản phẩm/trạng thái, chỉ số critic/evidence/SLA.
- Form tạo hồ sơ bám toàn bộ trường đầu vào BA.
- Xem trước route và validation trước khi chạy workflow mock.

Review gate: tạo được hồ sơ cho cả hai sản phẩm; các node thay đổi đúng theo product và AML.

## Phase 4 — Case workbench

- Tổng quan khách hàng và khoản đề nghị.
- Visual workflow canvas kiểu node-based studio; phân biệt business, AI/RAG và control nodes.
- Mock runner 10–15 giây, connector animation và node inspector hiển thị input/output.
- Input/output được diễn giải bằng tiếng Việt cho nhân viên nghiệp vụ, không hiển thị JSON thô.
- Mỗi node có citation; citation lỗi liên kết tới đúng tài liệu, chỉ số hoặc artifact cần kiểm tra.
- Có thư viện và trang chi tiết cho từng citation: nguyên văn, nội dung đầy đủ, điều khoản, hiệu lực, provenance, hash, lý do áp dụng và dữ liệu hồ sơ được đối chiếu.
- Sau khi workflow kiểm chứng hoàn tất, frontend tạo báo cáo yêu cầu bổ sung cho doanh nghiệp và hỗ trợ xuất Word hoặc in/lưu PDF chuẩn A4.
- Mock cases bao phủ thiếu tài liệu, lệch thuế, AML, CIC, dòng tiền thấp, lợi nhuận âm và khách hàng ngoài phạm vi.
- Document completeness; financial/tax metrics.
- Agent artifacts, warnings, proposed actions, critic verdict.
- Evidence/citation validation và execution trace.

Review gate: không có quyết định approve/reject; mọi blocker đều dẫn tới evidence request hoặc HITL.

## Phase 5 — Quality review

- Build TypeScript/Vite.
- Kiểm tra responsive và các empty/loading state chính.
- Đối chiếu lại field/component/workflow với BA và ghi rõ điểm chờ backend contract.
