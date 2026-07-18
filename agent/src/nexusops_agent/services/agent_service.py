from __future__ import annotations

from nexusops_agent.contracts.case import CaseContext
from nexusops_agent.contracts.hitl import AgentResolutionPackage, HumanReviewTask, ProposedAction
from nexusops_agent.orchestration.rework import BoundedReworkController
from nexusops_agent.workflows.runner import AgentWorkflowRunner


class AgentService:
    """Backend-facing adapter. It returns artifacts; it never writes banking systems."""

    def __init__(self, runner: AgentWorkflowRunner | None = None) -> None:
        self.runner = runner or AgentWorkflowRunner()
        self.rework = BoundedReworkController()

    def run_case(self, case: CaseContext) -> AgentResolutionPackage:
        state = self.runner.run(case)
        if state.critic_verdict == "REVISE":
            self.rework.apply_once(state, lambda: self.runner.execute_node(state, "MANDATORY_CRITIC"))
            self.runner._finalize(state)

        blockers = [finding.reason for finding in state.critic_findings]
        warnings = [
            reason
            for result in state.citation_results.values()
            for reason in result.reasons
        ]
        tasks: list[HumanReviewTask] = []
        if any(name == "COMPLIANCE_AGENT" and artifact.status != "PASS" for name, artifact in state.artifacts.items()):
            tasks.append(HumanReviewTask(task_type="COMPLIANCE_REVIEW", case_id=case.case_id, priority="HIGH", reason_codes=["KYC_AML_TRIGGER"]))
        if any(name == "CREDIT_AGENT" and artifact.status != "PASS" for name, artifact in state.artifacts.items()):
            tasks.append(HumanReviewTask(task_type="CREDIT_REVIEW", case_id=case.case_id, priority="HIGH", reason_codes=["CREDIT_READINESS_UNRESOLVED"]))
        if not tasks and state.final_status != "READY_FOR_HUMAN_REVIEW":
            tasks.append(HumanReviewTask(task_type="DATA_REVIEW", case_id=case.case_id, reason_codes=["EVIDENCE_OR_DOCUMENT_GAP"]))

        actions: list[ProposedAction] = []
        for artifact in state.artifacts.values():
            for action_type in artifact.proposed_actions:
                actions.append(
                    ProposedAction(
                        action_type=action_type,
                        payload={"case_id": case.case_id},
                        risk="MEDIUM",
                        requires_human_approval=True,
                    )
                )
        citations = [
            {"claim_id": claim_id, "status": result.status, "reasons": result.reasons}
            for claim_id, result in state.citation_results.items()
        ]
        return AgentResolutionPackage(
            case_id=case.case_id,
            final_status=state.final_status,
            critic_verdict=state.critic_verdict,
            route=state.route,
            blockers=blockers,
            warnings=warnings,
            citations=citations,
            human_tasks=tasks,
            proposed_actions=actions,
            external_write_executed=False,
            trace=state.trace,
        )
