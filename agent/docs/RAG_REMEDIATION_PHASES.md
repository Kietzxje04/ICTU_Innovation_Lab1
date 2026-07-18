# Legal RAG remediation phases

Mục tiêu của kế hoạch này là thay corpus pháp luật hiện tại bằng một pipeline có thể tái tạo, kiểm toán và fail-closed. Mỗi phase phải có test, commit riêng và review diff trước khi phase kế tiếp bắt đầu.

## Phase 1 — Registry và quality gates

- Tạo document registry làm nguồn metadata cấp văn bản.
- Tách xác minh nguồn/hiệu lực khỏi chất lượng chunk.
- Audit xung đột định danh, nguồn thiếu, hash thiếu và hiệu lực chưa xác minh.
- Không tự động nâng `REVIEW_REQUIRED` thành `ACCEPTED`.

Tiêu chí hoàn thành:

- Registry từ chối `document_id` trùng.
- Văn bản chính thức thiếu URL, source hash hoặc hiệu lực đã xác minh phải fail closed.
- Audit hiện trạng xuất được số chunk searchable/quarantine/rejected và mã cảnh báo.

## Phase 2 — Structural legal parser/chunker

- Parse theo Phần/Chương/Mục/Điều/Khoản/Điểm.
- Ghép nội dung bị ngắt qua trang trước khi chunk.
- Không cắt giữa Khoản hoặc Điểm.
- Phân loại preamble, article, appendix, table và signature.

Tiêu chí hoàn thành:

- Chunk quy phạm luôn có Điều cha.
- Chunk con có `parent_id`, `heading_path` và citation xác định.
- Bộ fixture kiểm tra Điều ngắn, Điều dài, Khoản/Điểm và nội dung qua trang đều đạt.

## Phase 3 — Corpus build pipeline

- Sinh `accepted`, `quarantine`, `rejected` dưới dạng JSONL.
- Sinh manifest có hash nguồn, số lượng và namespace.
- Chỉ dữ liệu đạt registry gate và chunk gate mới vào accepted.

Tiêu chí hoàn thành:

- Build có tính quyết định: cùng input tạo cùng output/hash.
- Không có chunk trùng ID/hash.
- Corpus accepted không chứa nguồn chưa xác minh.

## Phase 4 — Loader và retrieval

- Loader đọc corpus generated thay cho file normalized thủ công.
- Lọc theo domain, product tag và topic tag.
- Kết hợp lexical/vector/reranker và mở rộng parent/neighbor.

Tiêu chí hoàn thành:

- Agent nghiệp vụ không thể đọc quarantine.
- Data Reviewer có thể đọc quarantine có kiểm soát.
- Citation vẫn là substring chính xác của `content`.

## Phase 5 — Migration và evaluation

- Chạy lại transformer trên nguồn đã xác minh.
- Bổ sung corpus chính sách sản phẩm cho Corporate Overdraft và Working Capital.
- Xây tập câu hỏi chuẩn và đo Recall@5/citation validity.
- Chạy workflow end-to-end và kiểm tra `NO_PRODUCT_EVIDENCE`.

Tiêu chí hoàn thành:

- Không còn cảnh báo thiếu evidence cho sản phẩm có căn cứ trong corpus.
- Truy vấn không có căn cứ phải abstain, không tự suy diễn.
- Toàn bộ test agent/backend liên quan đều đạt.
