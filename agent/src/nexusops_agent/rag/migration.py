from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from nexusops_agent.contracts.evidence import EvidenceChunk


class MigrationReport(BaseModel):
    total_chunks: int
    product_tag_counts: dict[str, int] = Field(default_factory=dict)
    topic_tag_counts: dict[str, int] = Field(default_factory=dict)
    unresolved_quality_warnings: dict[str, int] = Field(default_factory=dict)


class CorpusMetadataMigrator:
    """Deterministic metadata enrichment; never promotes chunk quality or legal validity."""

    PRODUCT_RULES = {
        "CORPORATE_OVERDRAFT": ("thấu chi", "corporate overdraft"),
        "WORKING_CAPITAL": ("vốn lưu động", "working capital"),
    }
    TOPIC_RULES = {
        "ELIGIBILITY": ("điều kiện", "đối tượng áp dụng"),
        "REQUIRED_DOCUMENTS": ("tài liệu", "hồ sơ"),
        "AML": ("rửa tiền", "aml"),
        "SUSPICIOUS_TRANSACTION": ("giao dịch đáng ngờ",),
        "ACCOUNT_TURNOVER": ("doanh số", "vòng quay", "dòng tiền"),
    }

    def migrate(self, chunks: list[EvidenceChunk]) -> tuple[list[EvidenceChunk], MigrationReport]:
        migrated: list[EvidenceChunk] = []
        product_counts: Counter[str] = Counter()
        topic_counts: Counter[str] = Counter()
        unresolved: Counter[str] = Counter()
        for chunk in chunks:
            searchable_text = "\n".join(filter(None, [chunk.title, chunk.article_title, chunk.embedding_text])).casefold()
            product_tags = sorted(set(chunk.product_tags) | {
                tag for tag, needles in self.PRODUCT_RULES.items() if any(needle in searchable_text for needle in needles)
            })
            topic_tags = sorted(set(chunk.topic_tags) | {
                tag for tag, needles in self.TOPIC_RULES.items() if any(needle in searchable_text for needle in needles)
            })
            product_counts.update(product_tags)
            topic_counts.update(topic_tags)
            unresolved.update(chunk.quality.warnings)
            migrated.append(chunk.model_copy(update={"product_tags": product_tags, "topic_tags": topic_tags}))
        return migrated, MigrationReport(
            total_chunks=len(migrated),
            product_tag_counts=dict(sorted(product_counts.items())),
            topic_tag_counts=dict(sorted(topic_counts.items())),
            unresolved_quality_warnings=dict(sorted(unresolved.items())),
        )
