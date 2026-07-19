from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from nexusops_agent.contracts.evidence import EvidenceChunk

from .loader import RagCorpus
from .namespace_router import Namespace, namespace_for


TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ỹĐđ_]+", re.UNICODE)


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFC", value).casefold()
    return set(TOKEN_RE.findall(normalized))


@dataclass(frozen=True)
class RetrievalHit:
    chunk: EvidenceChunk
    namespace: Namespace
    score: float


class HybridLiteRetriever:
    """Deterministic lexical baseline; replaceable by vector+BM25 adapter."""

    def __init__(self, corpus: RagCorpus) -> None:
        self.corpus = corpus

    def search(
        self,
        query: str,
        allowed_namespaces: set[Namespace],
        *,
        top_k: int = 6,
        allow_review_required: bool = False,
        product: str | None = None,
        topics: set[str] | None = None,
    ) -> list[RetrievalHit]:
        query_tokens = _tokens(query)
        normalized_topics = {topic.casefold() for topic in (topics or set())}
        hits: list[RetrievalHit] = []
        for chunk in self.corpus.load():
            namespace = namespace_for(chunk)
            if namespace not in allowed_namespaces:
                continue
            if namespace == Namespace.QUARANTINE and not allow_review_required:
                continue
            if product and chunk.product_tags and product not in chunk.product_tags:
                continue
            document_tokens = _tokens(chunk.embedding_text)
            overlap = len(query_tokens & document_tokens)
            if overlap == 0:
                continue
            product_bonus = 0.25 if product and product in chunk.product_tags else 0.0
            topic_bonus = 0.1 * len(normalized_topics & {topic.casefold() for topic in chunk.topic_tags})
            score = overlap / max(len(query_tokens), 1) + product_bonus + topic_bonus
            hits.append(RetrievalHit(chunk=chunk, namespace=namespace, score=score))
        return sorted(hits, key=lambda item: (-item.score, item.chunk.chunk_id))[:top_k]
