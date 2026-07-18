# Phase 1 Review Checklist

- [x] Chỉ thay đổi trong folder `agent`.
- [x] RAG JSON không bị ghi đè.
- [x] FPT base URL cấu hình qua environment.
- [x] API key không có trong source/config.
- [x] Model registry có role/fallback/temperature/max_tokens.
- [x] Planner deterministic-first.
- [x] Credit và Critic dùng model family khác nhau.
- [x] Voice model được đánh dấu out-of-scope MVP.
- [x] Provider adapter không in secret khi repr/error.
- [x] Existing tests vẫn pass.

## Chưa đóng ở Phase 1

- Chưa gọi live chat completion vì key đã lộ và cần rotate trước.
- Chưa benchmark latency/cost thực tế theo key mới.
- Chưa publish vector index; thực hiện ở Phase 2.
