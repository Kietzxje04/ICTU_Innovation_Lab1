Mở 2 terminal tại thư mục chứa 

Terminal 1 — Backend:

```bash
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Backend chạy tại:
API: http://localhost:8000
Swagger: http://localhost:8000/docs
Health check: http://localhost:8000/health

Terminal 2 — Frontend:

```bash
cd frontend
npm.cmd run dev
```

Sau đó mở địa chỉ Vite hiển thị trong terminal, thường là:
http://localhost:5173