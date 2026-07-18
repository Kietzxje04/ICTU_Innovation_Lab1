from __future__ import annotations

from dataclasses import dataclass

from nexusops_agent.providers.fpt_factory import FptAiFactoryClient

from .retriever import RetrievalHit


@dataclass
class FptReranker:
    client: FptAiFactoryClient
    model: str = "bge-reranker-v2-m3"

    def rerank(self, query: str, hits: list[RetrievalHit], *, top_n: int = 6) -> list[RetrievalHit]:
        if not hits:
            return []
        response = self.client.rerank(
            model=self.model,
            query=query,
            documents=[hit.chunk.content for hit in hits],
            top_n=min(top_n, len(hits)),
        )
        results = response.get("results") or response.get("data")
        if not isinstance(results, list):
            raise ValueError("Reranker response missing results list")
        reranked: list[RetrievalHit] = []
        for item in results:
            index = int(item["index"])
            score = float(item.get("relevance_score", item.get("score", 0.0)))
            original = hits[index]
            reranked.append(RetrievalHit(chunk=original.chunk, namespace=original.namespace, score=score))
        return reranked[:top_n]
