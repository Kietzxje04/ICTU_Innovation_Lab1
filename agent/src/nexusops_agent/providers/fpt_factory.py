from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ProviderConfig:
    base_url: str
    api_key: str
    timeout_seconds: float = 60.0
    max_retries: int = 2

    def __repr__(self) -> str:
        return f"ProviderConfig(base_url={self.base_url!r}, api_key='<redacted>', timeout_seconds={self.timeout_seconds!r}, max_retries={self.max_retries!r})"


class FptAiFactoryError(RuntimeError):
    pass


class FptAiFactoryClient:
    """Minimal OpenAI-compatible client for FPT AI Factory.

    The key is held in memory only and is never included in errors, traces or
    repr output. No request is made until a caller explicitly invokes a method.
    """

    def __init__(self, config: ProviderConfig) -> None:
        if not config.api_key:
            raise ValueError("FPT AI Factory API key cannot be empty")
        self.config = config

    @property
    def base_url(self) -> str:
        return self.config.base_url.rstrip("/")

    def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self.base_url}/{path.lstrip('/')}",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "NexusOps-Agent/0.1",
            },
        )
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            try:
                with urlopen(request, timeout=self.config.timeout_seconds) as response:
                    parsed = json.loads(response.read().decode("utf-8"))
                    if not isinstance(parsed, dict):
                        raise FptAiFactoryError("Provider response must be a JSON object")
                    return parsed
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.config.max_retries:
                    time.sleep(min(2**attempt, 4))
        raise FptAiFactoryError(f"FPT AI Factory request failed after retries: {type(last_error).__name__}") from last_error

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 1200,
        response_format: dict[str, Any] | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format
        if tools is not None:
            payload["tools"] = tools
        return self._request("chat/completions", payload)

    def embeddings(self, *, model: str, inputs: list[str]) -> dict[str, Any]:
        return self._request("embeddings", {"model": model, "input": inputs})

    def rerank(self, *, model: str, query: str, documents: list[str], top_n: int = 6) -> dict[str, Any]:
        return self._request(
            "rerank",
            {"model": model, "query": query, "documents": documents, "top_n": top_n},
        )


def build_provider_from_settings(settings: Any) -> FptAiFactoryClient:
    return FptAiFactoryClient(
        ProviderConfig(
            base_url=settings.fpt_ai_base_url,
            api_key=settings.require_fpt_api_key(),
            timeout_seconds=settings.fpt_ai_timeout_seconds,
            max_retries=settings.fpt_ai_max_retries,
        )
    )
