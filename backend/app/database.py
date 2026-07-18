from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def create_schema() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "postgresql":
        # Lightweight additive migration for existing local Docker/pgAdmin
        # databases. It is intentionally non-destructive and idempotent.
        columns = {
            "account_history_months": "INTEGER",
            "twelve_month_credit_turnover": "DOUBLE PRECISION",
            "average_monthly_credit_inflow": "DOUBLE PRECISION",
            "turnover_stability_ratio": "DOUBLE PRECISION",
            "expected_utilization_ratio": "DOUBLE PRECISION",
            "negative_balance_days": "INTEGER",
            "cleanup_days": "INTEGER",
            "overdraft_purpose": "VARCHAR(255)",
            "loan_purpose": "VARCHAR(255)",
            "account_conduct_flags": "JSON",
        }
        with engine.begin() as connection:
            for name, ddl_type in columns.items():
                connection.execute(text(f'ALTER TABLE cases ADD COLUMN IF NOT EXISTS "{name}" {ddl_type}'))


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
