from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_role
from app.models.user import User

from pydantic import BaseModel

router = APIRouter()


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool
    is_verified: bool
    company: str | None = None
    title: str | None = None
    last_login_at: Any = None
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = None
    company: str | None = None
    title: str | None = None
    preferences: str | None = None


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    user_id = current_user.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    update_data: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    user_id = current_user.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user
