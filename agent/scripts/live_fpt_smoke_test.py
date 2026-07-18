from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nexusops_agent.config import Settings
from nexusops_agent.providers.fpt_factory import build_provider_from_settings


def _message_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("Chat response missing choices")
    message = choices[0].get("message", {})
    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("Chat response missing text content")
    return content.strip()


def _run(name: str, model: str, call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = call()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        content = _message_content(response)
        return {
            "name": name,
            "model": model,
            "status": "PASS",
            "latency_ms": elapsed_ms,
            "preview": content[:500],
            "usage": response.get("usage", {}),
        }
    except Exception as exc:
        return {
            "name": name,
            "model": model,
            "status": "FAIL",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "error_type": type(exc).__name__,
            "error": str(exc)[:300],
        }


def main() -> None:
    settings = Settings.from_env()
    client = build_provider_from_settings(settings)
    json_format = {"type": "json_object"}
    tests: list[dict[str, Any]] = []

    tests.append(_run(
        "planner_fallback",
        "DeepSeek-V4-Flash",
        lambda: client.chat_completion(
            model="DeepSeek-V4-Flash",
            messages=[
                {"role": "system", "content": "Bạn là Planner của NexusOps. Chỉ trả JSON gồm tasks và reasons. Không phê duyệt tín dụng."},
                {"role": "user", "content": "Khách hàng SME hiện hữu muốn vay vốn lưu động, thiếu tờ khai thuế và có chênh lệch doanh thu."},
            ],
            temperature=0.0,
            max_tokens=500,
        ),
    ))
    tests.append(_run(
        "product_agent",
        "SaoLa3.1-medium",
        lambda: client.chat_completion(
            model="SaoLa3.1-medium",
            messages=[
                {"role": "system", "content": "Phân loại nhu cầu vào CORPORATE_OVERDRAFT hoặc WORKING_CAPITAL. Trả JSON, không tự bịa policy."},
                {"role": "user", "content": "Doanh nghiệp cần bổ sung tiền nhập nguyên vật liệu trong 6 tháng."},
            ],
            temperature=0.0,
            max_tokens=220,
            response_format=json_format,
        ),
    ))
    tests.append(_run(
        "credit_reasoner",
        "Qwen3.6-27B",
        lambda: client.chat_completion(
            model="Qwen3.6-27B",
            messages=[
                {"role": "system", "content": "Bạn là Credit Readiness Agent. Chỉ dùng metrics được cung cấp. Trả JSON với status chỉ được là READY_FOR_HUMAN_REVIEW, NEEDS_MORE_EVIDENCE hoặc BLOCKED_OUT_OF_SCOPE; không dùng APPROVE/REJECT."},
                {"role": "user", "content": "product=WORKING_CAPITAL; tax_revenue_gap=0.18; missing_documents=[TAX_DECLARATION]; cic_bad_debt=false"},
            ],
            temperature=0.0,
            max_tokens=1200,
            response_format=json_format,
        ),
    ))
    tests.append(_run(
        "mandatory_critic",
        "gpt-oss-120b",
        lambda: client.chat_completion(
            model="gpt-oss-120b",
            messages=[
                {"role": "system", "content": "Bạn là Mandatory Critic. Trả JSON verdict PASS|REVISE|ESCALATE và findings. Nếu có unsupported claim, missing document, conflict hoặc invalid citation thì bắt buộc REVISE; PASS chỉ khi findings rỗng. Không tiết lộ chain-of-thought."},
                {"role": "user", "content": "Artifact nói hồ sơ đủ điều kiện nhưng tax gap=18%, thiếu tờ khai thuế và không có citation hợp lệ."},
            ],
            temperature=0.0,
            max_tokens=500,
            response_format=json_format,
        ),
    ))

    embedding_started = time.perf_counter()
    try:
        embedding_response = client.embeddings(
            model="Vietnamese_Embedding",
            inputs=[
                "query: điều kiện vay vốn lưu động SME",
                "passage: doanh nghiệp cần bổ sung vốn cho hoạt động sản xuất kinh doanh",
            ],
        )
        vectors = embedding_response.get("data", [])
        tests.append({
            "name": "embedding",
            "model": "Vietnamese_Embedding",
            "status": "PASS",
            "latency_ms": round((time.perf_counter() - embedding_started) * 1000, 2),
            "vector_count": len(vectors),
            "dimensions": len(vectors[0].get("embedding", [])) if vectors else 0,
        })
    except Exception as exc:
        tests.append({"name": "embedding", "model": "Vietnamese_Embedding", "status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:300]})

    rerank_started = time.perf_counter()
    try:
        rerank_response = client.rerank(
            model="bge-reranker-v2-m3",
            query="điều kiện vay vốn lưu động",
            documents=[
                "Điều kiện bổ sung vốn lưu động phục vụ sản xuất kinh doanh.",
                "Quy định báo cáo giao dịch đáng ngờ.",
                "Thông tin về sản phẩm thấu chi doanh nghiệp.",
            ],
            top_n=2,
        )
        results = rerank_response.get("results") or rerank_response.get("data") or []
        tests.append({
            "name": "reranker",
            "model": "bge-reranker-v2-m3",
            "status": "PASS",
            "latency_ms": round((time.perf_counter() - rerank_started) * 1000, 2),
            "result_count": len(results),
            "top_indices": [item.get("index") for item in results[:2]],
        })
    except Exception as exc:
        tests.append({"name": "reranker", "model": "bge-reranker-v2-m3", "status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)[:300]})

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "base_url": settings.fpt_ai_base_url,
        "contains_pii": False,
        "key_logged": False,
        "passed": sum(item["status"] == "PASS" for item in tests),
        "failed": sum(item["status"] == "FAIL" for item in tests),
        "tests": tests,
    }
    output = ROOT / "runtime" / "evaluations" / "fpt-live-smoke.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
