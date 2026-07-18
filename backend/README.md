# NexusOps Backend

FastAPI backend kết nối trực tiếp với package `nexusops-agent`. Agent contracts là nguồn dữ liệu chuẩn; các schema `Company` chỉ là projection tương thích frontend hiện tại.

## Cài đặt

```powershell
cd D:\D\abc\backend
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
```

## Chạy

```powershell
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Agent health: http://localhost:8000/api/agent/health
- RAG inventory: http://localhost:8000/api/agent/rag/inventory

SQLite được tạo tại `backend/runtime/nexusops.db`. RAG corpus trong `agent/final_rag_data_normalized_v1.json` chỉ được đọc, không bị chỉnh sửa.

## Full API test

```powershell
cd D:\D\abc\backend
.\.venv313\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv313\Scripts\python.exe -m unittest tests.test_full_api -v
```
