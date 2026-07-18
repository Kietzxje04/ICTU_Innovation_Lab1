from nexusops_agent.contracts.hitl import CriticFinding
from nexusops_agent.contracts.live import LiveCriticReview
from nexusops_agent.contracts.state import AgentArtifact, WorkflowState
from nexusops_agent.providers.structured import FptStructuredReasoner

from .base import BaseAgent


class MandatoryCriticAgent(BaseAgent):
    agent_id = "MANDATORY_CRITIC"
    engine = "GPT_OSS_120B_STRUCTURED_OR_DETERMINISTIC_BASELINE"

    def __init__(self, reasoner: FptStructuredReasoner | None = None) -> None:
        self.reasoner = reasoner

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
        summary = f"Critic verdict={verdict}; findings={len(findings)}"
        warnings = [f"{finding.finding_type}:{finding.target_id}" for finding in findings]
        raw = {
            "verdict": verdict,
            "findings": [finding.model_dump(mode="json") for finding in findings],
            "rework_allowed": verdict == "REVISE",
        }
        engine = self.engine
        if self.reasoner is not None:
            try:
                invocation = self.reasoner.invoke(
                    "mandatory_critic", "critic",
                    {"deterministic_verdict": verdict, "deterministic_findings": raw["findings"],
                     "artifacts": {name: {"status": artifact.status, "summary": artifact.summary, "warnings": artifact.warnings}
                                    for name, artifact in state.artifacts.items() if name != self.agent_id},
                     "citation_results": {key: value.model_dump(mode="json") for key, value in state.citation_results.items()},
                     "boundary": "Never downgrade deterministic blockers and never override hard rules."},
                    LiveCriticReview,
                )
                live = invocation.result
                rank = {"PASS": 0, "REVISE": 1, "ESCALATE": 2}
                verdict = max((verdict, live.verdict), key=rank.__getitem__)
                summary = live.summary
                warnings.extend(f"LIVE_CRITIC:{item}" for item in live.findings)
                raw.update({"live_model": invocation.model, "live_review": live.model_dump(mode="json"), "live_usage": invocation.usage})
                engine = "FPT_AI_FACTORY_MANDATORY_CRITIC"
            except Exception as exc:
                warnings.append(f"LIVE_AI_UNAVAILABLE:MANDATORY_CRITIC:{type(exc).__name__}")
                raw["live_error_type"] = type(exc).__name__
                engine = "DETERMINISTIC_MANDATORY_CRITIC_LIVE_FALLBACK"
        state.critic_verdict = verdict
        raw["verdict"] = verdict
        raw["rework_allowed"] = verdict == "REVISE"
        return AgentArtifact(
            agent_id=self.agent_id,
            engine=engine,
            status="PASS" if verdict == "PASS" else "REVIEW_REQUIRED",
            summary=summary,
            warnings=warnings,
            raw=raw,
        )
