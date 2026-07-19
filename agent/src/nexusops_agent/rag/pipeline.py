from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .policy import policy_for
from .retriever import HybridLiteRetriever, RetrievalHit


class Reranker(Protocol):
    def rerank(self, query: str, hits: list[RetrievalHit], *, top_n: int = 6) -> list[RetrievalHit]: ...


@dataclass
class RetrievalPipeline:
    lexical: HybridLiteRetriever
    reranker: Reranker | None = None
    reranker_fail_open: bool = True

    def retrieve(
        self,
        *,
        agent_id: str,
        query: str,
        demo_mode: bool = True,
        top_k: int = 6,
        product: str | None = None,
        topics: set[str] | None = None,
    ) -> list[RetrievalHit]:
        policy = policy_for(agent_id, demo_mode=demo_mode)
        candidates = self.lexical.search(
            query,
            set(policy.namespaces),
            top_k=max(top_k * 3, 12),
            allow_review_required=policy.allow_review_required,
            product=product,
            topics=topics,
        )
        if self.reranker is not None:
            try:
                return self.reranker.rerank(query, candidates, top_n=top_k)
            except Exception:
                if not self.reranker_fail_open:
                    raise
        return candidates[:top_k]
