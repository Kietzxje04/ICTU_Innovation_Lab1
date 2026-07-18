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

## Frontend readiness contract

Frontend mới dùng các field `CaseContext`, `WorkflowState`, `EvidenceItem` và `ReadinessCase`. Backend cung cấp:

```text
GET  /api/readiness/cases
GET  /api/readiness/cases/{case_id}
POST /api/readiness/cases
```

`POST /api/readiness/cases` nhận JSON dạng:

```json
{
  "company_name": "Example Company",
  "owner": "Relationship Manager",
  "context": {
    "case_id": "CASE-001",
    "customer_id": "CUS-001",
    "existing_customer": true,
    "product": "WORKING_CAPITAL",
    "requested_amount": 5000000000,
    "relationship_months": 24,
    "submitted_documents": [],
    "required_documents": [],
    "annual_revenue": null,
    "pretax_profit_last_2_years": [],
    "tax_declared_revenue": null,
    "cic_bad_debt": false,
    "kyc_aml_flags": [],
    "metadata": {}
  }
}
```

SQLite được tạo tại `backend/runtime/nexusops.db`. RAG corpus trong `agent/final_rag_data_normalized_v1.json` chỉ được đọc, không bị chỉnh sửa.

## Full API test

```powershell
cd D:\D\abc\backend
.\.venv313\Scripts\python.exe -m pip install -r requirements-test.txt
.\.venv313\Scripts\python.exe -m unittest tests.test_full_api -v
```
