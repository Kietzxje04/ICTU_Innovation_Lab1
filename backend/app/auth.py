from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_session
from .exceptions import DomainError
from .models import AuthSessionRecord, RoleRecord, UserRecord

ROLE_EMPLOYEE = "EMPLOYEE"
ROLE_MANAGER = "MANAGER"
ROLE_DIRECTOR = "DIRECTOR"
ROLE_ORDER = {ROLE_EMPLOYEE: 0, ROLE_MANAGER: 1, ROLE_DIRECTOR: 2}


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000).hex()
    return f"pbkdf2_sha256$180000${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class CurrentUser:
    record: UserRecord
    role: RoleRecord


def current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise DomainError(401, "AUTHENTICATION_REQUIRED", "Vui lòng đăng nhập để tiếp tục")
    token_hash = hashlib.sha256(authorization[7:].encode()).hexdigest()
    auth_session = session.get(AuthSessionRecord, token_hash)
    expires_at = auth_session.expires_at if auth_session else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not auth_session or not expires_at or expires_at <= datetime.now(timezone.utc):
        raise DomainError(401, "INVALID_SESSION", "Phiên đăng nhập không hợp lệ hoặc đã hết hạn")
    user = session.get(UserRecord, auth_session.user_id)
    role = session.get(RoleRecord, user.role_id) if user else None
    if not user or not user.is_active or not role:
        raise DomainError(403, "USER_DISABLED", "Tài khoản không còn hoạt động")
    return CurrentUser(user, role)


def role_can_approve(role_id: str, amount: float) -> bool:
    if role_id == ROLE_DIRECTOR:
        return amount >= 1_000_000_000
    if role_id == ROLE_MANAGER:
        return amount < 1_000_000_000
    return role_id == ROLE_EMPLOYEE and amount < 500_000_000


def next_role(role_id: str) -> str | None:
    return {ROLE_EMPLOYEE: ROLE_MANAGER, ROLE_MANAGER: ROLE_DIRECTOR}.get(role_id)


def seed_roles_and_users(session: Session) -> None:
    roles = [
        (ROLE_EMPLOYEE, "Nhân viên", 499_999_999.0, ["cases:view", "cases:upload", "loans:check", "loans:approve", "loans:transfer"]),
        (ROLE_MANAGER, "Quản lý", 999_999_999.0, ["cases:view", "cases:upload", "loans:check", "loans:transfer", "loans:approve"]),
        (ROLE_DIRECTOR, "Giám đốc", None, ["cases:view", "cases:upload", "loans:check", "loans:transfer", "loans:approve"]),
    ]
    for role_id, name, limit, permissions in roles:
        if not session.get(RoleRecord, role_id):
            session.add(RoleRecord(role_id=role_id, name=name, approval_limit=limit, permissions=permissions))
    accounts = [
        ("director-1", "giamdoc@nexusops.local", "Nguyễn Văn Giám đốc", ROLE_DIRECTOR),
        ("manager-1", "quanly1@nexusops.local", "Trần Minh Quản lý", ROLE_MANAGER),
        ("manager-2", "quanly2@nexusops.local", "Lê Thu Quản lý", ROLE_MANAGER),
        ("manager-3", "quanly3@nexusops.local", "Phạm Hoàng Quản lý", ROLE_MANAGER),
    ] + [(f"employee-{i}", f"chuyenvien{i}@nexusops.local", f"Chuyên viên {i}", ROLE_EMPLOYEE) for i in range(1, 6)]
    for username, email, full_name, role_id in accounts:
        if not session.scalar(select(UserRecord).where(UserRecord.username == username)):
            session.add(UserRecord(user_id=username, username=username, password_hash=hash_password("NexusOps@2026", username), email=email, full_name=full_name, role_id=role_id))
    session.commit()


def create_session(session: Session, user: UserRecord) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    session.add(AuthSessionRecord(token_hash=hashlib.sha256(token.encode()).hexdigest(), user_id=user.user_id, expires_at=expires))
    session.commit()
    return token, expires
