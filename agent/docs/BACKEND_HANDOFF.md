# Backend Handoff Contract

Backend team import `AgentService`; không import trực tiếp specialist, RAG store hoặc provider client.

```python
from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.services import AgentService

package = AgentService().run_case(CaseContext.model_validate(request_payload))
return package.model_dump(mode="json")
```

## Input

`CaseContext` gồm customer/product/requested amount, document codes, financial/tax fields, CIC và KYC/AML flags. Backend chịu trách nhiệm authentication, authorization, PII masking và mapping từ API schema sang contract này.

## Output

`AgentResolutionPackage`:

- `final_status`: readiness state, không phải credit decision.
- `critic_verdict`: PASS/REVISE/ESCALATE.
- `route`: node IDs phục vụ React Flow.
- `citations`: validation status theo claim.
- `human_tasks`: task cần Credit/Compliance/Data reviewer.
- `proposed_actions`: luôn `requires_human_approval=true`.
- `trace`: node events cho SSE/dashboard.
- `external_write_executed`: luôn false trong Agent Layer.

## Suggested backend endpoint

```text
POST /api/v1/agent/runs
GET  /api/v1/agent/runs/{case_id}
GET  /api/v1/agent/runs/{case_id}/events
```

Backend không được trả API key/model headers về frontend và không log raw provider request.
