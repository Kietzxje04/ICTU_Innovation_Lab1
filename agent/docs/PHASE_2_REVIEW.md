# Phase 2 Review Checklist

- [x] RAG input được đọc read-only.
- [x] Namespace quarantine tách khỏi searchable mặc định.
- [x] Compliance Agent chỉ được phép query `legal_aml`.
- [x] Credit/Product Agent được phép query `legal_lending` và `demo_internal_policy` trong demo mode.
- [x] Embedding adapter dùng `Vietnamese_Embedding`, có fallback registry.
- [x] Reranker adapter dùng `bge-reranker-v2-m3`.
- [x] Index manifest lưu source SHA-256, namespace counts và model versions.
- [x] Citation Validator vẫn kiểm exact quote/hash/quality/validity.
- [x] Không ghi vector/index vào file data gốc.

## Chưa đóng ở Phase 2

- Chưa gọi live embedding/rerank vì API key cần rotate và set qua environment.
- `legal_lending` hiện chưa có chunk `ACCEPTED`; đây là data gap phải review/recrawl, không được che bằng cách hạ quality gate.
