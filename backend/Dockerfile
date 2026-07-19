FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

COPY agent /workspace/agent
COPY backend /workspace/backend

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install /workspace/agent \
    && sed -e 's/\r$//' -e '/^-e \.\.\/agent$/d' /workspace/backend/requirements.txt > /tmp/backend-requirements.txt \
    && python -m pip install -r /tmp/backend-requirements.txt \
    && mkdir -p /workspace/backend/runtime \
                 /workspace/agent/runtime/indexes \
                 /workspace/agent/runtime/traces \
                 /workspace/agent/runtime/evaluations \
                 /workspace/agent/runtime/rag/generated \
    && chmod +x /workspace/backend/docker-entrypoint.sh

WORKDIR /workspace/backend

ENV DATABASE_URL=postgresql+psycopg://nexusops:nexusops_dev_password@postgres:5432/nexusops \
    NEXUSOPS_AGENT_ROOT=/workspace/agent \
    NEXUSOPS_RAG_DATA_PATH=/workspace/agent/runtime/rag/generated/accepted.jsonl \
    NEXUSOPS_CONFIG_DIR=/workspace/agent/configs \
    NEXUSOPS_RUNTIME_DIR=/workspace/agent/runtime \
    NEXUSOPS_AI_MODE=deterministic \
    NEXUSOPS_DEMO_MODE=true \
    NEXUSOPS_ALLOW_REVIEW_REQUIRED=false \
    NEXUSOPS_ENABLE_MOCK_APIS=false \
    SEED_DEMO_DATA=false \
    FRONTEND_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import json, urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)); assert data['data']['status']=='ok'"

CMD ["/workspace/backend/docker-entrypoint.sh"]
