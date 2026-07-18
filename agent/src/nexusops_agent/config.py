from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    rag_data_path: Path
    config_dir: Path
    runtime_dir: Path
    demo_mode: bool = True
    allow_review_required: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            rag_data_path=Path(os.getenv("NEXUSOPS_RAG_DATA_PATH", PACKAGE_ROOT / "final_rag_data_normalized_v1.json")),
            config_dir=Path(os.getenv("NEXUSOPS_CONFIG_DIR", PACKAGE_ROOT / "configs")),
            runtime_dir=Path(os.getenv("NEXUSOPS_RUNTIME_DIR", PACKAGE_ROOT / "runtime")),
            demo_mode=_as_bool(os.getenv("NEXUSOPS_DEMO_MODE"), True),
            allow_review_required=_as_bool(os.getenv("NEXUSOPS_ALLOW_REVIEW_REQUIRED"), False),
        )
