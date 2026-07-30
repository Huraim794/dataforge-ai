from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    role: str = "user",
    project_ids: Optional[list[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    now = datetime.now(timezone.utc)
    to_encode: Dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "iss": settings.jwt_issuer,
        "type": "access",
    }
    if project_ids:
        to_encode["projects"] = project_ids
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    to_encode = {
        "sub": user_id,
        "iat": now,
        "iss": settings.jwt_issuer,
        "type": "refresh",
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def verify_token(
    token: str, expected_type: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        token_type = payload.get("type", "access")
        if expected_type and token_type != expected_type:
            return None
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    return verify_token(token, expected_type="access")


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    return verify_token(token, expected_type="refresh")


def verify_api_key_sync(raw_key: str, db_session) -> Optional[str]:
    """Synchronous version for use inside async contexts where session is available."""
    from app.models.user import APIKey
    from sqlalchemy import select

    key_hash = hash_api_key(raw_key)
    result = db_session.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active,
        )
    )
    key = result.scalar_one_or_none()
    if key:
        return key.user_id
    return None


def hash_api_key(api_key: str) -> str:
    return sha256(api_key.encode()).hexdigest()


def generate_api_key() -> str:
    import secrets

    return f"df_{secrets.token_urlsafe(32)}"
