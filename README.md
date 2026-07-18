# NexusOps AI

Hệ thống gồm React frontend, FastAPI backend và NexusOps Agent Layer.

## 1. Chạy backend

Lần đầu:

```powershell
cd D:\D\abc\backend
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
```

Mỗi lần chạy:

```powershell
cd D:\D\abc\backend
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## 2. Chạy frontend

```powershell
cd D:\D\abc\frontend
npm.cmd install
npm.cmd run dev
```

Mở http://localhost:5173. Swagger API ở http://localhost:8000/docs.
