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
    ) -> list[RetrievalHit]:
        query_tokens = _tokens(query)
        hits: list[RetrievalHit] = []
        for chunk in self.corpus.load():
            namespace = namespace_for(chunk)
            if namespace not in allowed_namespaces:
                continue
            if namespace == Namespace.QUARANTINE and not allow_review_required:
                continue
            document_tokens = _tokens(chunk.embedding_text)
            overlap = len(query_tokens & document_tokens)
            if overlap == 0:
                continue
            score = overlap / max(len(query_tokens), 1)
            hits.append(RetrievalHit(chunk=chunk, namespace=namespace, score=score))
        return sorted(hits, key=lambda item: (-item.score, item.chunk.chunk_id))[:top_k]
