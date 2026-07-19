#!/bin/sh
set -eu

python /workspace/agent/scripts/build_gated_rag_corpus.py \
  --corpus /workspace/agent/final_rag_data_normalized_v1.json \
  --registry /workspace/agent/configs/rag/document_registry.json \
  --output-dir /workspace/agent/runtime/rag/generated

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
