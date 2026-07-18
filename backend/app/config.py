from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_url: str
    cors_origins: tuple[str, ...]
    api_prefix: str
    agent_root: Path

    @classmethod
    def from_env(cls) -> "Settings":
        default_db = (BACKEND_ROOT / "runtime" / "nexusops.db").resolve().as_posix()
        origins = tuple(
            value.strip()
            for value in os.getenv(
                "FRONTEND_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if value.strip()
        )
        return cls(
            app_name="NexusOps AI Backend",
            database_url=os.getenv("DATABASE_URL", f"sqlite:///{default_db}"),
            cors_origins=origins,
            api_prefix="/api",
            agent_root=Path(os.getenv("NEXUSOPS_AGENT_ROOT", WORKSPACE_ROOT / "agent")).resolve(),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
