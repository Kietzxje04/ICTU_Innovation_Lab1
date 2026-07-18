from __future__ import annotations

from dataclasses import dataclass

from .namespace_router import Namespace


@dataclass(frozen=True)
class RetrievalPolicy:
    agent_id: str
    namespaces: frozenset[Namespace]
    allow_review_required: bool = False


def policy_for(agent_id: str, *, demo_mode: bool = True) -> RetrievalPolicy:
    normalized = agent_id.upper()
    if normalized == "COMPLIANCE_AGENT":
        return RetrievalPolicy(agent_id=normalized, namespaces=frozenset({Namespace.LEGAL_AML}))
    if normalized in {"PRODUCT_AGENT", "CREDIT_AGENT"}:
        namespaces = {Namespace.LEGAL_LENDING}
        if demo_mode:
            namespaces.add(Namespace.DEMO_INTERNAL_POLICY)
        return RetrievalPolicy(agent_id=normalized, namespaces=frozenset(namespaces))
    if normalized == "DATA_REVIEWER":
        return RetrievalPolicy(
            agent_id=normalized,
            namespaces=frozenset({Namespace.QUARANTINE}),
            allow_review_required=True,
        )
    raise ValueError(f"Agent has no retrieval policy: {agent_id}")
