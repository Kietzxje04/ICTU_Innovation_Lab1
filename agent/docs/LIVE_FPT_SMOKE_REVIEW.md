# Live FPT AI Factory Smoke Review

Thời điểm test: 2026-07-18. Input hoàn toàn synthetic, không chứa PII. API key không xuất hiện trong report/log.

| Sample | Model | Result | Latency quan sát |
|---|---|---|---:|
| Planner fallback | DeepSeek-V4-Flash | PASS | 2869.59 ms |
| Product classification | SaoLa3.1-medium | PASS | 630.94 ms |
| Credit reasoning | Qwen3.6-27B | PASS | 5875.10 ms |
| Mandatory Critic | gpt-oss-120b | PASS | 1806.88 ms |
| Vietnamese embedding | Vietnamese_Embedding | PASS, 1024 dimensions | 525.67 ms |
| Evidence reranking | bge-reranker-v2-m3 | PASS | 1953.21 ms |

## Findings

- DeepSeek reasoning mode không ổn định khi ép `response_format=json_object`; planner fallback dùng JSON instruction nhưng không ép response format.
- Qwen3.6-27B cần completion budget đủ lớn vì reasoning tokens có thể chiếm phần lớn giới hạn.
- Critic prompt phải khóa invariant: có finding thì verdict không được PASS.
- Embedding cold call từng có latency cao do retry/cold start; warm call nhanh hơn đáng kể.
- Không dùng output model làm credit decision; output vẫn qua typed schema, Critic, Citation Validator và Policy Gate.

Raw redacted report: `runtime/evaluations/fpt-live-smoke.json`.
