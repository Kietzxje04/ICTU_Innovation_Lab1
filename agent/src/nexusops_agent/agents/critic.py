from nexusops_agent.contracts.hitl import CriticFinding
from nexusops_agent.contracts.state import AgentArtifact, WorkflowState

from .base import BaseAgent


class MandatoryCriticAgent(BaseAgent):
    agent_id = "MANDATORY_CRITIC"
    engine = "GPT_OSS_120B_STRUCTURED_OR_DETERMINISTIC_BASELINE"

    def run(self, state: WorkflowState) -> AgentArtifact:
        findings: list[CriticFinding] = []
        for name, artifact in state.artifacts.items():
            if name == self.agent_id:
                continue
            if artifact.status in {"BLOCKED", "REVIEW_REQUIRED"}:
                findings.append(
                    CriticFinding(
                        finding_id=f"CF-{len(findings) + 1:03d}",
                        finding_type="UNRESOLVED_ARTIFACT",
                        target_id=name,
                        severity="HIGH" if artifact.status == "BLOCKED" else "MEDIUM",
                        reason=artifact.summary,
                        required_action="ESCALATE_OR_SUPPLY_EVIDENCE",
                    )
                )
        invalid_citation_statuses = {
            "REVIEW_REQUIRED",
            "STALE_OR_UNVERIFIED",
            "INVALID_QUOTE",
            "INVALID_HASH",
            "INVALID_AUTHORITY",
            "ABSTAIN_NO_EVIDENCE",
        }
        for claim_id, result in state.citation_results.items():
            if result.status in invalid_citation_statuses:
                findings.append(
                    CriticFinding(
                        finding_id=f"CF-{len(findings) + 1:03d}",
                        finding_type="INVALID_CITATION",
                        target_id=claim_id,
                        severity="HIGH",
                        reason=result.status,
                        required_action="REMOVE_CLAIM_OR_RETRIEVE_VALID_EVIDENCE",
                    )
                )
        state.critic_findings = findings
        if not findings:
            verdict = "PASS"
        elif state.rework_count >= 1:
            verdict = "ESCALATE"
        else:
            verdict = "REVISE"
        state.critic_verdict = verdict
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=self.engine,
            status="PASS" if verdict == "PASS" else "REVIEW_REQUIRED",
            summary=f"Critic verdict={verdict}; findings={len(findings)}",
            warnings=[f"{finding.finding_type}:{finding.target_id}" for finding in findings],
            raw={
                "verdict": verdict,
                "findings": [finding.model_dump(mode="json") for finding in findings],
                "rework_allowed": verdict == "REVISE",
            },
        )
