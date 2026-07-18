# Live Legal RAG Samples Review

Thời điểm test: 2026-07-18. Pipeline: local lexical retrieval → FPT `bge-reranker-v2-m3` → Citation Validator → `Llama-3.3-70B-Instruct`.

| Sample | Retrieval | LLM | Total | Technical | Legal/Safety assessment |
|---|---:|---:|---:|---|---|
| Khách hàng rủi ro cao | 747.82 ms | 4408.37 ms | 5156.62 ms | PASS | `STALE_OR_UNVERIFIED`; explanation only, deterministic warning/HITL |
| Báo cáo giao dịch đáng ngờ | 770.72 ms | 3165.01 ms | 3936.34 ms | PASS | Nội dung hợp lý nhưng nguồn `UNVERIFIED`; LLM đã abstain |
| Giao dịch giá trị lớn | 1037.54 ms | 2456.19 ms | 3494.40 ms | PASS/PARTIAL | Evidence chưa đủ nên câu trả lời thiếu nhóm thông tin; cần retrieve/review thêm |
| Hiệu lực 15/2025/TT-NHNN | 2230.82 ms | 2681.25 ms | 4915.02 ms | PASS | `REVIEW_REQUIRED` vì filename/content mismatch; bắt buộc Data Reviewer |

## Kết luận

- API/RAG/reranker/LLM pipeline hoạt động 4/4.
- Citation exact chunk/document/article được trả về đầy đủ.
- Không sample nào đủ điều kiện trở thành hard legal rule do `validity_status=UNVERIFIED`.
- LLM đôi khi để `abstain=false` dù nguồn chưa xác minh; Citation Validator/Policy Gate phải override LLM.
- Sample giao dịch giá trị lớn chứng minh corpus còn thiếu/fragmented; không được để LLM tự hoàn thiện bằng kiến thức nền.

Raw redacted report: `runtime/evaluations/live-legal-samples.json`.
