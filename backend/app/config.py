from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = BACKEND_ROOT.parent
DEFAULT_DATABASE_URL = "postgresql+psycopg://nexusops:nexusops_dev_password@localhost:5432/nexusops"


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    database_url: str
    cors_origins: tuple[str, ...]
    api_prefix: str
    agent_root: Path
    seed_demo_data: bool
    environment: str
    enable_mock_apis: bool

    @classmethod
    def from_env(cls) -> "Settings":
        environment = os.getenv("NEXUSOPS_ENV", "production").strip().casefold()
        database_url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        if environment != "test" and not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must use PostgreSQL (postgresql+psycopg://)")
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
            database_url=database_url,
            cors_origins=origins,
            api_prefix="/api",
            agent_root=Path(os.getenv("NEXUSOPS_AGENT_ROOT", WORKSPACE_ROOT / "agent")).resolve(),
            seed_demo_data=_as_bool(os.getenv("SEED_DEMO_DATA"), False),
            environment=environment,
            enable_mock_apis=_as_bool(os.getenv("NEXUSOPS_ENABLE_MOCK_APIS"), environment == "test"),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()
