from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _load_local_env(path: Path) -> None:
    """Load simple KEY=VALUE entries without logging or overwriting process env."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env(PACKAGE_ROOT / ".env")


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _path_from_env(name: str, default: Path) -> Path:
    value = Path(os.getenv(name, str(default)))
    return value if value.is_absolute() else (PACKAGE_ROOT / value).resolve()


@dataclass(frozen=True)
class Settings:
    rag_data_path: Path
    config_dir: Path
    runtime_dir: Path
    demo_mode: bool = True
    allow_review_required: bool = False
    ai_mode: str = "deterministic"
    fpt_ai_base_url: str = "https://mkp-api.fptcloud.com/v1"
    fpt_ai_api_key: str | None = field(default=None, repr=False)
    fpt_ai_timeout_seconds: float = 60.0
    fpt_ai_max_retries: int = 2

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            rag_data_path=_path_from_env("NEXUSOPS_RAG_DATA_PATH", PACKAGE_ROOT / "final_rag_data_normalized_v1.json"),
            config_dir=_path_from_env("NEXUSOPS_CONFIG_DIR", PACKAGE_ROOT / "configs"),
            runtime_dir=_path_from_env("NEXUSOPS_RUNTIME_DIR", PACKAGE_ROOT / "runtime"),
            demo_mode=_as_bool(os.getenv("NEXUSOPS_DEMO_MODE"), True),
            allow_review_required=_as_bool(os.getenv("NEXUSOPS_ALLOW_REVIEW_REQUIRED"), False),
            ai_mode=os.getenv("NEXUSOPS_AI_MODE", "deterministic").strip().casefold(),
            fpt_ai_base_url=os.getenv("FPT_AI_BASE_URL", "https://mkp-api.fptcloud.com/v1").rstrip("/"),
            fpt_ai_api_key=os.getenv("FPT_AI_API_KEY") or None,
            fpt_ai_timeout_seconds=float(os.getenv("FPT_AI_TIMEOUT_SECONDS", "60")),
            fpt_ai_max_retries=int(os.getenv("FPT_AI_MAX_RETRIES", "2")),
        )

    def require_fpt_api_key(self) -> str:
        if not self.fpt_ai_api_key:
            raise RuntimeError("FPT_AI_API_KEY is not configured; set it in a local .env or process environment")
        return self.fpt_ai_api_key

    @property
    def live_ai_enabled(self) -> bool:
        return self.ai_mode == "live"
