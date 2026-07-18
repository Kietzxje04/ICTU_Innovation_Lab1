from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "final_rag_data_normalized_v1.json"


def main() -> None:
    raw_bytes = DATA.read_bytes()
    records = json.loads(raw_bytes.decode("utf-8"))
    ids = [item["chunk_id"] for item in records]
    hashes = [item["content_hash"] for item in records]
    billing_remaining = any("beeknoee.com/billing" in item["content"].casefold() for item in records)
    assert len(ids) == len(set(ids)), "duplicate chunk_id"
    assert len(hashes) == len(set(hashes)), "duplicate content_hash"
    assert not billing_remaining, "billing error remains in corpus"
    assert all(not item["is_synthetic"] or item.get("synthetic_disclaimer") for item in records)
    report = {
        "file": str(DATA),
        "sha256": hashlib.sha256(raw_bytes).hexdigest().upper(),
        "records": len(records),
        "quality": dict(Counter(item["quality"]["status"] for item in records)),
        "domain": dict(Counter(item["domain"] for item in records)),
        "billing_error_remaining": billing_remaining,
        "unique_chunk_ids": True,
        "unique_content_hashes": True,
    }
    json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
