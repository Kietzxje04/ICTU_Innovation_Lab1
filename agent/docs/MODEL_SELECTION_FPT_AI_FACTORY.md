# Model Selection — FPT AI Factory

Base URL đã kiểm tra read-only qua endpoint `/v1/models`: `https://mkp-api.fptcloud.com/v1`. API key không lưu trong repository; cấu hình qua `FPT_AI_API_KEY`.

## Quyết định dùng cho MVP

| Role | Model | Vì sao chọn | Khi không gọi |
|---|---|---|---|
| Planner/Router | Deterministic Python; fallback `DeepSeek-V4-Flash` | Route/rule cần ổn định; Flash có tools/structured output và latency/cost tốt | Request rõ và rule đủ |
| Document Classifier | `SaoLa3.1-medium` | Nhẹ, phù hợp tiếng Việt, đủ phân loại/checklist | Document đã có type tin cậy |
| Vision Document Extractor | `Qwen2.5-VL-7B-Instruct` | Nhận ảnh/PDF page và trích xuất field | Input đã là JSON/text sạch |
| Product Agent | `SaoLa3.1-medium` | Chi phí thấp, xử lý mô tả nhu cầu và tiếng Việt | Product code đã xác định |
| Credit Agent | `Qwen3.6-27B` | Reasoning/structured output, context lớn; chỉ gọi sau deterministic metrics | Case chỉ thiếu giấy tờ đơn giản |
| Compliance Agent | `Llama-3.3-70B-Instruct` | Tách model family khỏi Credit, xử lý evidence/cross-domain tốt | Không có KYC/AML trigger |
| Mandatory Critic | `gpt-oss-120b` | Model family độc lập, reasoning/tool/structured output | Không được tắt; luôn chạy |
| Escalation | `GLM-5.2` | Context rất lớn, dùng cho conflict/rework thất bại | Không có conflict hoặc case P0 |
| Embedding | `Vietnamese_Embedding` | Tối ưu retrieval tiếng Việt | Fallback `multilingual-e5-large` |
| Reranker | `bge-reranker-v2-m3` | Rerank multilingual/legal evidence | Không bỏ nếu top-k > 6 |

## Không đưa vào critical path MVP

- Whisper/FPT.AI-VITs: voice không thuộc hai workflow loan-readiness hiện tại.
- Gemma multimodal: giữ làm fallback benchmark cho vision, không thêm vào đường găng.
- GLM-5.1: fallback cho Credit, không gọi đồng thời nhiều model.

## Parameter policy

- Deterministic nodes: không LLM, temperature không áp dụng.
- Product/Document: temperature `0.0–0.1`, output JSON schema.
- Credit/Compliance: temperature `0.0–0.1`, chỉ nhận typed tools/evidence.
- Critic: temperature `0.0`, chỉ nhận artifacts/citations; không nhận hidden chain-of-thought.
- Max one rework; provider retry bounded tối đa 2 lần.

## Security policy

```text
.env local → ProviderConfig (memory only)
→ Authorization header
→ response redaction
→ trace chỉ lưu model_id/latency/status/token estimate
```

Không log request headers, API key, raw PII hoặc full provider response.
