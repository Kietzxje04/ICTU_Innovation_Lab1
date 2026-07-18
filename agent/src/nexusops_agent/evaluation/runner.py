from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.services.agent_service import AgentService


class EvaluationRunner:
    def __init__(self, service: AgentService | None = None) -> None:
        self.service = service or AgentService()

    def run_file(self, path: Path) -> dict[str, Any]:
        scenarios = json.loads(path.read_text(encoding="utf-8"))
        results: list[dict[str, Any]] = []
        citation_statuses: Counter[str] = Counter()
        started = time.perf_counter()
        for scenario in scenarios:
            case = CaseContext.model_validate(scenario["case"])
            package = self.service.run_case(case)
            expected = scenario["expected"]
            checks = {
                "final_status": package.final_status == expected["final_status"],
                "critic_verdict": package.critic_verdict == expected["critic_verdict"],
                "route_contains": all(node in package.route for node in expected["route_contains"]),
                "route_excludes": all(node not in package.route for node in expected["route_excludes"]),
                "no_external_write": package.external_write_executed is False,
                "mandatory_tail": package.route[-3:] == ["MANDATORY_CRITIC", "CITATION_VALIDATOR", "POLICY_GATE"],
            }
            for citation in package.citations:
                citation_statuses[citation["status"]] += 1
            results.append(
                {
                    "scenario_id": scenario["scenario_id"],
                    "passed": all(checks.values()),
                    "checks": checks,
                    "actual": {
                        "final_status": package.final_status,
                        "critic_verdict": package.critic_verdict,
                        "route": package.route,
                        "human_task_count": len(package.human_tasks),
                        "trace_event_count": len(package.trace),
                    },
                }
            )
        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "scenario_count": len(results),
            "passed": sum(result["passed"] for result in results),
            "failed": sum(not result["passed"] for result in results),
            "pass_rate": sum(result["passed"] for result in results) / max(len(results), 1),
            "elapsed_ms": round(elapsed_ms, 3),
            "citation_statuses": dict(citation_statuses),
            "results": results,
        }
