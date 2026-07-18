# NexusOps AI

Hệ thống gồm React frontend, FastAPI backend, PostgreSQL và NexusOps Agent Layer.

## Chạy bằng Docker

Yêu cầu Docker Desktop đang chạy ở chế độ Linux containers.

```powershell
cd D:\D\abc
Copy-Item .env.example .env
docker compose up --build -d
```

Các địa chỉ sau khi khởi động:

- Frontend Docker: http://localhost:3000
- Frontend Vite local: http://localhost:5173
- Backend: http://localhost:8000
- Swagger: http://localhost:8000/docs hoặc http://localhost:3000/docs
- PostgreSQL: `localhost:5432`

Theo dõi log:

```powershell
docker compose logs -f
```

Dừng hệ thống nhưng giữ database:

```powershell
docker compose down
```

Xóa cả container và dữ liệu PostgreSQL/runtime:

```powershell
docker compose down -v
```

## Kết nối PostgreSQL bằng pgAdmin4

pgAdmin4 là công cụ quản trị; PostgreSQL Server được Docker Compose chạy trong service `postgres`.

Tạo server connection trong pgAdmin4:

```text
Host name/address: localhost
Port:              5432
Maintenance DB:    nexusops
Username:          nexusops
Password:          nexusops_dev_password
```

Các giá trị lấy từ file `.env`. Nếu máy đã có PostgreSQL chiếm cổng 5432, đặt `POSTGRES_PORT=5433` trong `.env` và dùng cổng 5433 trong pgAdmin4.

Database được lưu trong Docker volume `nexusops_postgres-data`. Backend mặc định chỉ tạo schema, không tự seed dữ liệu demo. Bật `SEED_DEMO_DATA=true` trong `.env` nếu muốn nạp các case mẫu từ `backend/app/seed.py`.

Nếu volume đã có dữ liệu cũ, việc recreate container không xóa dữ liệu. Muốn làm sạch database demo, chỉ khi chấp nhận xóa toàn bộ dữ liệu, chạy `docker compose down -v` rồi `docker compose up --build -d`.

Muốn seed thủ công vào database đang chạy:

```powershell
docker compose exec backend python -m app.seed
```

Không cần `FPT_AI_API_KEY` để chạy deterministic demo workflow. Muốn bật live FPT AI Factory, điền key vào `.env` cục bộ; không commit file này.

## Chạy local không dùng Docker

Backend:

```powershell
cd D:\D\abc\backend
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg://nexusops:nexusops_dev_password@localhost:5432/nexusops"
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend chỉ hỗ trợ PostgreSQL runtime. Nếu `DATABASE_URL` dùng scheme khác PostgreSQL, ứng dụng sẽ dừng với lỗi cấu hình.

Frontend:

```powershell
cd D:\D\abc\frontend
npm.cmd install
npm.cmd run dev
```

## Luồng dữ liệu readiness

```text
React intake
  -> FastAPI (validation, PostgreSQL, audit)
  -> NexusOps Agent (product schema, document matrix, routing, metrics, Critic)
  -> FastAPI persists WorkflowState/artifacts
  -> React displays Agent output
```

- Frontend không dùng `mock-data.ts` làm nguồn dữ liệu runtime và không tự quyết workflow.
- Ma trận tài liệu và route preview được tải từ Agent thông qua backend.
- PostgreSQL là nguồn lưu trữ duy nhất cho case/run/artifact/citation/action.
- `SEED_DEMO_DATA=false` nghĩa là database mới không có hồ sơ cho tới khi người dùng tạo hồ sơ hoặc seed thủ công.
- Các ngưỡng trong config sản phẩm là `SYNTHETIC_DEMO_POLICY`, không phải chính sách tín dụng chính thức.

Corporate Overdraft được mô hình hóa là hạn mức quay vòng trên tài khoản thanh toán. Readiness xem xét lịch sử tài khoản, doanh số ghi Có 12 tháng, dòng tiền bình quân tháng, độ ổn định, tỷ lệ hạn mức đề nghị/dòng tiền, hành vi cleanup, CIC/KYC/AML và đối chiếu tài chính-thuế. Hệ thống không tự quyết định hạn mức, lãi suất, phê duyệt hoặc từ chối tín dụng.

Tạo thêm 1.000 hồ sơ mock vào PostgreSQL đang chạy:

```powershell
docker compose exec backend python -m app.seed --count 1000
```

Lệnh này không xóa dữ liệu cũ và chạy lại sẽ bỏ qua các ID đã tồn tại.

## Chạy live AI

API key FPT AI Factory được đọc từ `agent/.env` và truyền vào container qua `docker-compose.yml`; không commit file key này.

```powershell
cd D:\D\abc
docker compose up --build -d
```

Kiểm tra runtime:

```powershell
(Invoke-RestMethod http://localhost:8000/api/agent/health).data
```

Kỳ vọng `mode=live`, `provider=FPT_AI_FACTORY`, `demo_mode=false`. Công thức và hard rule readiness vẫn deterministic; live AI diễn giải Product/Credit/Compliance và chạy Mandatory Critic có cấu trúc.

Các API `/mock/*` bị tắt trong live mode. Connector thật tới LOS/DMS/BPM/GRC, Core Banking, CIC và KYC/AML chưa có trong repository; action approval sẽ trả `LIVE_CONNECTOR_NOT_CONFIGURED` cho tới khi tích hợp endpoint thật. Hệ thống không giả lập external write trong live mode.
