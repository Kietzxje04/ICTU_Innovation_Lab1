# NexusOps Backend

## Live AI runtime

Docker Compose đọc secret từ `agent/.env` tại runtime. Compose mặc định dùng `NEXUSOPS_AI_MODE=live`, `NEXUSOPS_DEMO_MODE=false` và `NEXUSOPS_ENABLE_MOCK_APIS=false`.

Product Agent, Credit Agent, Compliance Agent và Mandatory Critic gọi FPT AI Factory với structured JSON output. Hard rules, công thức tài chính, document matrix và status readiness vẫn deterministic và có quyền ưu tiên cao hơn output AI.

Danh sách case không tự chạy AI cho hồ sơ chưa có assessment. Agent chỉ chạy khi tạo case hoặc mở chi tiết, tránh gọi model hàng loạt cho dữ liệu seed.

FastAPI backend kết nối với package `nexusops-agent`, lưu case/run/artifact/citation/action trong PostgreSQL và cung cấp dữ liệu cho React frontend.

## Chạy bằng Docker Compose

Từ thư mục gốc:

```powershell
cd D:\D\abc
Copy-Item .env.example .env
docker compose up --build -d
```

Backend image cài package `agent` từ cùng build context. PostgreSQL được lưu trong volume `nexusops_postgres-data`; runtime index/trace/evaluation của agent được lưu trong `nexusops_agent-runtime`. Frontend Docker mở tại http://localhost:3000. Docker mặc định không seed case mẫu; đặt `SEED_DEMO_DATA=true` trong `.env` hoặc chạy `docker compose exec backend python -m app.seed` nếu cần dữ liệu demo.

## Chạy local

```powershell
cd D:\D\abc\backend
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg://nexusops:nexusops_dev_password@localhost:5432/nexusops"
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Trong Docker, `DATABASE_URL` trỏ tới service PostgreSQL `postgres`. Khi chạy backend trực tiếp trên máy, dùng `postgresql+psycopg://nexusops:nexusops_dev_password@localhost:5432/nexusops`. Backend không hỗ trợ SQLite runtime.

## API chính

```text
GET  /health
GET  /api/agent/health
GET  /api/agent/rag/inventory

GET  /api/readiness/cases
POST /api/readiness/cases
GET  /api/readiness/cases/{case_id}

GET  /api/v3/products
GET  /api/v3/products/{product}/intake-schema
POST /api/v3/cases/preview-route

POST /api/v1/agent/runs
GET  /api/v1/agent/runs/{case_id}
GET  /api/v1/agent/runs/{case_id}/events
```

Swagger: http://localhost:8000/docs

Các API product/schema/preview đọc trực tiếp cấu hình và router của package Agent. Khi tạo case, backend thay `required_documents` do client gửi bằng ma trận chuẩn của Agent trước khi ghi PostgreSQL. Các cột thấu chi mới được thêm bằng migration cộng dồn, không xóa dữ liệu cũ.

Các trường thấu chi chính: `account_history_months`, `twelve_month_credit_turnover`, `average_monthly_credit_inflow`, `turnover_stability_ratio`, `expected_utilization_ratio`, `negative_balance_days`, `cleanup_days`, `overdraft_purpose`, `account_conduct_flags`.

## Kiểm thử

```powershell
cd D:\D\abc\backend
.\.venv313\Scripts\python.exe -m unittest discover -s tests -v
```

Test Agent contract và routing:

```powershell
cd D:\D\abc
.\backend\.venv313\Scripts\python.exe -m unittest discover -s agent/tests -v
```

Tạo thêm 1.000 hồ sơ mock trong PostgreSQL, không xóa dữ liệu cũ và chạy lại không tạo trùng:

```powershell
cd D:\D\abc\backend
.\.venv313\Scripts\python.exe -m app.seed --count 1000
```

Nếu backend chạy trong Docker:

```powershell
docker compose exec backend python -m app.seed --count 1000
```

## Tài khoản RBAC mẫu

Lệnh seed cũng tạo 1 Giám đốc, 3 Quản lý và 5 Nhân viên. Mật khẩu dùng chung cho môi trường phát triển là `NexusOps@2026`.

| Vai trò | Tài khoản |
|---|---|
| Giám đốc | `director-1` |
| Quản lý | `manager-1`, `manager-2`, `manager-3` |
| Nhân viên | `employee-1` đến `employee-5` |

API luồng phê duyệt:

- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/cases/{case_id}/loan-approval`
- `POST /api/cases/{case_id}/loan-approval/approve`
- `POST /api/cases/{case_id}/loan-approval/transfer`

ID được tạo theo dạng `MOCK-WC-000001` và `MOCK-OD-000001`. Có thể dùng prefix khác, ví dụ `--prefix DEMO`.

API danh sách mặc định trả tối đa 100 hồ sơ để không kích hoạt workflow cho toàn bộ dữ liệu cùng lúc. Dùng `limit` và `offset` để phân trang, ví dụ `/api/readiness/cases?limit=100&offset=100`.
