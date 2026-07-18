from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.config import Settings
from nexusops_agent.contracts.evidence import CitationClaim
from nexusops_agent.providers.fpt_factory import build_provider_from_settings
from nexusops_agent.rag.citation_validator import CitationValidator
from nexusops_agent.rag.loader import RagCorpus
from nexusops_agent.rag.pipeline import RetrievalPipeline
from nexusops_agent.rag.reranker import FptReranker
from nexusops_agent.rag.retriever import HybridLiteRetriever


SAMPLES = [
    {
        "id": "AML_HIGH_RISK_CUSTOMER",
        "agent_id": "COMPLIANCE_AGENT",
        "query": "khách hàng có rủi ro cao biện pháp tăng cường phòng chống rửa tiền",
        "question": "Khách hàng được đánh giá rủi ro cao thì tổ chức báo cáo cần làm gì?",
    },
    {
        "id": "SUSPICIOUS_TRANSACTION_REPORT",
        "agent_id": "COMPLIANCE_AGENT",
        "query": "báo cáo giao dịch đáng ngờ nội dung trách nhiệm tổ chức báo cáo",
        "question": "Khi phát hiện giao dịch đáng ngờ, cần xử lý và báo cáo như thế nào?",
    },
    {
        "id": "LARGE_VALUE_TRANSACTION",
        "agent_id": "COMPLIANCE_AGENT",
        "query": "giao dịch có giá trị lớn nội dung báo cáo thông tin khách hàng",
        "question": "Báo cáo giao dịch có giá trị lớn cần có những nhóm thông tin nào?",
    },
    {
        "id": "CURRENT_REVIEW_REQUIRED_2025",
        "agent_id": "DATA_REVIEWER",
        "query": "Thông tư 15/2025/TT-NHNN hiệu lực Điều 13 phòng chống rửa tiền",
        "question": "Văn bản 15/2025/TT-NHNN quy định gì về hiệu lực thi hành?",
    },
]


def _extract_content(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        raise ValueError("CHAT_RESPONSE_MISSING_CHOICES")
    message = choices[0].get("message", {})
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("CHAT_RESPONSE_MISSING_FINAL_CONTENT")
    return content.strip()


def main() -> None:
    settings = Settings.from_env()
    corpus = RagCorpus(settings.rag_data_path)
    validator = CitationValidator(corpus.by_id())
    provider = build_provider_from_settings(settings)
    pipeline = RetrievalPipeline(
        HybridLiteRetriever(corpus),
        reranker=FptReranker(provider),
    )
    reports: list[dict[str, Any]] = []

    for sample in SAMPLES:
        started = time.perf_counter()
        try:
            retrieve_started = time.perf_counter()
            hits = pipeline.retrieve(
                agent_id=sample["agent_id"],
                query=sample["query"],
                demo_mode=False,
                top_k=3,
            )
            retrieval_ms = round((time.perf_counter() - retrieve_started) * 1000, 2)

            citations: list[dict[str, Any]] = []
            evidence_blocks: list[str] = []
            for index, hit in enumerate(hits):
                chunk = hit.chunk
                quote = chunk.content[: min(420, len(chunk.content))]
                claim = CitationClaim(
                    claim_id=f"{sample['id']}-CIT-{index + 1}",
                    chunk_id=chunk.chunk_id,
                    quote=quote,
                    claim_type="LEGAL_EXPLANATION",
                )
                validation = validator.validate(claim)
                citations.append({
                    "chunk_id": chunk.chunk_id,
                    "document_number": chunk.document_number,
                    "article": chunk.article,
                    "page_or_part": chunk.page_or_part,
                    "quality_status": chunk.quality.status,
                    "validity_status": chunk.validity_status,
                    "citation_status": validation.status,
                    "citation_reason": validation.reasons,
                    "score": round(hit.score, 4),
                    "quote_preview": quote[:220],
                })
                evidence_blocks.append(
                    f"EVIDENCE_ID={chunk.chunk_id}\nDOCUMENT={chunk.document_number}\n"
                    f"QUALITY={chunk.quality.status}; VALIDITY={chunk.validity_status}\nQUOTE={quote}"
                )

            llm_started = time.perf_counter()
            llm_response = provider.chat_completion(
                model="Llama-3.3-70B-Instruct",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là Compliance Legal Evidence Agent. Trả JSON gồm answer, evidence_ids, "
                            "caveats và abstain. Chỉ dùng evidence được cung cấp; không tự bịa điều luật. "
                            "Nếu evidence có REVIEW_REQUIRED hoặc UNVERIFIED thì abstain=true hoặc caveats rõ ràng. "
                            "Không đưa ra quyết định tín dụng."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"QUESTION: {sample['question']}\n\n" + "\n\n".join(evidence_blocks),
                    },
                ],
                temperature=0.0,
                max_tokens=700,
                response_format={"type": "json_object"},
            )
            llm_ms = round((time.perf_counter() - llm_started) * 1000, 2)
            answer = _extract_content(llm_response)
            reports.append({
                "id": sample["id"],
                "status": "PASS",
                "agent_id": sample["agent_id"],
                "retrieved_count": len(hits),
                "retrieval_ms": retrieval_ms,
                "llm_model": "Llama-3.3-70B-Instruct",
                "llm_ms": llm_ms,
                "total_ms": round((time.perf_counter() - started) * 1000, 2),
                "citations": citations,
                "answer_preview": answer[:700],
                "usage": llm_response.get("usage", {}),
            })
        except Exception as exc:
            reports.append({
                "id": sample["id"],
                "status": "FAIL",
                "agent_id": sample["agent_id"],
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
                "total_ms": round((time.perf_counter() - started) * 1000, 2),
            })

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": settings.fpt_ai_base_url,
        "contains_pii": False,
        "key_logged": False,
        "sample_count": len(reports),
        "passed": sum(item["status"] == "PASS" for item in reports),
        "failed": sum(item["status"] == "FAIL" for item in reports),
        "samples": reports,
    }
    output = ROOT / "runtime" / "evaluations" / "live-legal-samples.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
