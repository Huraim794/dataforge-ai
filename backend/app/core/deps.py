from __future__ import annotations

from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import (
    hash_api_key,
    verify_access_token,
)
from app.models.user import APIKey

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_async_session():
        yield session


async def get_current_user(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    token = api_key or (bearer.credentials if bearer else None)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Try JWT access token first
    payload = verify_access_token(token)
    if payload:
        return payload

    # Try API key (look up SHA-256 hash in database)
    key_hash = hash_api_key(token)
    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active,
        )
    )
    api_key_record = result.scalar_one_or_none()
    if api_key_record:
        return {
            "sub": api_key_record.user_id,
            "role": "user",
            "type": "api_key",
            "key_id": api_key_record.id,
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict]:
    token = api_key or (bearer.credentials if bearer else None)
    if not token:
        return None

    # Try JWT access token
    payload = verify_access_token(token)
    if payload:
        return payload

    # Try API key
    key_hash = hash_api_key(token)
    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active,
        )
    )
    api_key_record = result.scalar_one_or_none()
    if api_key_record:
        return {
            "sub": api_key_record.user_id,
            "role": "user",
            "type": "api_key",
            "key_id": api_key_record.id,
        }
    return None


async def get_current_user_id(
    current_user: dict = Depends(get_current_user),
) -> str:
    sub = current_user.get("sub")
    if sub is None:
        raise ValueError("User ID not found in token")
    return str(sub)


def require_role(required_role: str):
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role", "user")
        roles: dict[str, int] = {"admin": 100, "user": 50, "viewer": 10}
        if roles.get(user_role, 0) < roles.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user_role}' insufficient. Required: '{required_role}'",
            )
        return current_user

    return role_checker


async def verify_project_access(
    project_id: str,
    user_id: str,
    db: AsyncSession,
    required_role: Optional[str] = None,
) -> bool:
    from app.models.project import ProjectMember

    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this project is denied",
        )
    if required_role:
        role_rank = {"owner": 100, "admin": 80, "member": 50}
        user_level = role_rank.get(membership.role.value, 0)
        required_level = role_rank.get(required_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient project role. Required: {required_role}",
            )
    return True
