from enum import StrEnum

from nexusops_agent.contracts.evidence import EvidenceChunk


class Namespace(StrEnum):
    LEGAL_AML = "legal_aml"
    LEGAL_LENDING = "legal_lending"
    DEMO_INTERNAL_POLICY = "demo_internal_policy"
    QUARANTINE = "quarantine_review_required"
    REJECTED = "rejected_not_indexed"


def namespace_for(chunk: EvidenceChunk) -> Namespace:
    if chunk.quality.status == "REJECTED":
        return Namespace.REJECTED
    if chunk.quality.status == "REVIEW_REQUIRED":
        return Namespace.QUARANTINE
    if chunk.quality.status == "DEMO_ONLY" or chunk.is_synthetic:
        return Namespace.DEMO_INTERNAL_POLICY
    if chunk.domain == "COMPLIANCE_AML":
        return Namespace.LEGAL_AML
    if chunk.domain == "LENDING_REGULATION":
        return Namespace.LEGAL_LENDING
    return Namespace.QUARANTINE
