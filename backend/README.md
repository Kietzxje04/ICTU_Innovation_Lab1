# NexusOps AI — Backend & Orchestration API

**Production:** [https://nexusopsai.site/](https://nexusopsai.site/)
**System overview:** [Root README](../README.md)
**Agent layer:** [Agent README](../agent/README.md)
**Frontend:** [Frontend README](../frontend/README.md)

Backend NexusOps AI là lớp FastAPI điều phối giữa React UI, PostgreSQL và package `nexusops-agent`. Backend chịu trách nhiệm xác thực, session, API contract, persistence, audit, workflow execution, RBAC, phê duyệt và chuyển cấp. Quy tắc chuyên môn và tác tử nằm trong Agent Layer; frontend không tự quyết định route hoặc chính sách.

## Trách nhiệm kiến trúc

| Thành phần backend | Trách nhiệm |
|---|---|
| Authentication | Đăng nhập bằng tài khoản PostgreSQL, tạo session và cookie HttpOnly |
| Authorization | RBAC Nhân viên, Quản lý, Giám đốc và kiểm tra thẩm quyền |
| Workflow API | Tạo run, chạy từng node theo phản hồi backend và lưu WorkflowState |
| Persistence | Lưu case, run, artifact, citation, event, action, approval và session |
| Approval Service | Kiểm tra readiness, hạn mức, chuyển cấp và lịch sử phê duyệt |
| Agent integration | Gọi product schema, router, specialist agents, critic và RAG |
| Auditability | Request ID, run events, timestamps, warnings và decision history |
| Production safety | Không giả lập external write khi live connector chưa cấu hình |

## Luồng request

```mermaid
sequenceDiagram
    participant U as React UI
    participant A as FastAPI
    participant DB as PostgreSQL
    participant O as Agent Orchestrator
    participant S as Specialist Agent
    participant C as Critic & Citation Validator

    U->>A: POST workflow run / node
    A->>DB: Validate session and load case state
    A->>O: Execute next permitted node
    O->>S: Structured specialist task
    S-->>O: Artifact, metrics, warnings, claims
    O->>C: Critique and validate evidence
    C-->>O: Verdict and validation results
    O-->>A: Updated WorkflowState
    A->>DB: Persist run, artifacts, citations and events
    A-->>U: HTTP response with completed node
    U->>U: Advance UI to next node
```

## API chính

| Method | Endpoint | Mục đích |
|---|---|---|
| `GET` | `/health` | Healthcheck backend |
| `GET` | `/api/agent/health` | Trạng thái Agent Layer/provider |
| `GET` | `/api/agent/rag/inventory` | Thống kê nguồn RAG |
| `POST` | `/api/auth/login` | Xác thực và tạo session cookie |
| `GET` | `/api/auth/me` | Kiểm tra phiên và lấy profile |
| `POST` | `/api/auth/logout` | Thu hồi session trong database |
| `GET` | `/api/readiness/cases` | Danh sách hồ sơ readiness |
| `POST` | `/api/readiness/cases` | Tạo hồ sơ mới |
| `GET` | `/api/readiness/cases/{case_id}` | Chi tiết hồ sơ và workflow |
| `POST` | `/api/cases/{case_id}/workflow-runs` | Khởi tạo workflow run |
| `POST` | `/api/cases/{case_id}/workflow-runs/{run_id}/nodes/{node}` | Chạy một node thực tế |
| `GET` | `/api/cases/{case_id}/loan-approval` | Kiểm tra quyền phê duyệt |
| `POST` | `/api/cases/{case_id}/loan-approval/approve` | Phê duyệt hồ sơ |
| `POST` | `/api/cases/{case_id}/loan-approval/transfer` | Chuyển hồ sơ lên cấp tiếp theo |
| `GET` | `/api/v3/products/{product}/intake-schema` | Schema tiếp nhận theo sản phẩm |
| `POST` | `/api/v3/cases/preview-route` | Xem route trước khi tạo hồ sơ |

Swagger local: [http://localhost:8000/docs](http://localhost:8000/docs)

## RBAC và phê duyệt

| Vai trò | Hạn mức | Kế thừa | Hành động khi vượt hạn mức |
|---|---:|---|---|
| Nhân viên | Dưới 500 triệu VND | Quyền xem, tải lên, kiểm tra và duyệt | Chuyển Quản lý |
| Quản lý | Dưới 1 tỷ VND | Toàn bộ quyền Nhân viên | Chuyển Giám đốc |
| Giám đốc | Không giới hạn | Toàn bộ quyền Quản lý | Cấp cao nhất |

Hạn mức không phải điều kiện duy nhất. Backend chỉ cho phép phê duyệt khi workflow đã hoàn tất, `final_status` là `READY_FOR_HUMAN_REVIEW` và Mandatory Critic trả `PASS`.

## Mô hình dữ liệu PostgreSQL

| Bảng | Dữ liệu lưu trữ |
|---|---|
| `cases` | Hồ sơ, dữ liệu tài chính, tài liệu, metadata và sản phẩm |
| `assessment_runs` | Route, trạng thái, critic verdict và final status |
| `agent_artifacts` | Output có cấu trúc của từng tác tử |
| `citation_results` | Claim, nguồn, validation status và reasons |
| `run_events` | Dấu vết từng node và timestamp |
| `proposed_actions` | Hành động đề xuất, phê duyệt và execution state |
| `roles`, `users` | RBAC và tài khoản |
| `auth_sessions` | Phiên đăng nhập được hash và thời hạn |
| `loan_approvals` | Cấp đang xử lý, người duyệt và lịch sử chuyển cấp |

## Chế độ deterministic và live

| Chế độ | AI interpretation | Hard rules | External mock API | Mục đích |
|---|---|---|---|---|
| Deterministic demo | Có thể dùng fallback xác định | Luôn bật | Có thể bật có kiểm soát | Demo tái lập và benchmark |
| Live | Provider được cấu hình qua environment | Luôn ưu tiên | Tắt mặc định | Production-like runtime |

Hard rules, công thức tài chính, document matrix và readiness status không bị model output ghi đè. Khi provider timeout, hệ thống ghi warning và dùng fallback theo cấu hình thay vì âm thầm tạo kết quả không truy nguyên.

## Khởi chạy

Từ thư mục gốc repository:

```powershell
Copy-Item .env.example .env
docker compose build backend
docker compose up -d backend
docker compose ps
```

Chạy backend local:

```powershell
cd backend
py -3.13 -m venv .venv313
.\.venv313\Scripts\python.exe -m pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg://nexusops:nexusops_dev_password@localhost:5432/nexusops"
.\.venv313\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

## Seed khởi tạo

```powershell
docker compose exec backend python -m app.seed --count 1000 --seed 20260718 --prefix MOCK --refresh
```

| Seed data | Kết quả |
|---|---|
| User RBAC | 1 Giám đốc, 3 Quản lý, 5 Nhân viên |
| Hồ sơ | 1.000 bản ghi mock |
| Sản phẩm | 500 Working Capital và 500 Corporate Overdraft |
| Scenario | 12 nhóm tình huống nghiệp vụ |
| Tính tái lập | Cố định bằng `--seed 20260718` |

## Nguyên tắc production

| Nguyên tắc | Cách backend đáp ứng |
|---|---|
| Không tin dữ liệu client | Backend chuẩn hóa schema và document matrix |
| Không dùng token đọc được bởi JavaScript | Session cookie HttpOnly và bản ghi database |
| Không phê duyệt vượt thẩm quyền | Approval Service kiểm tra role hierarchy và amount |
| Không quyết định khi thiếu bằng chứng | Critic, Citation Validator và Policy Gate |
| Không ghi external system ngoài kiểm soát | Approval, idempotency và connector configuration |
| Có thể kiểm toán | Persist run, artifact, event, citation và approval history |

## Production transition

Production website là [https://nexusopsai.site/](https://nexusopsai.site/). Repository hiện vẫn chứa test/evaluation phục vụ kiểm chứng kỹ thuật. Việc dọn test/debug cần được thực hiện trong một thay đổi riêng có kiểm soát; seed khởi tạo phải được giữ lại để tạo tài khoản và dữ liệu ban đầu.
