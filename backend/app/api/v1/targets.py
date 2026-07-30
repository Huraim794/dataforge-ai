from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dataforge.backend.app.core.deps import (
    get_current_user,
    get_db,
    verify_project_access,
)
from pydantic import BaseModel

from dataforge.backend.app.models.target import Target, TargetType

router = APIRouter()


class TargetCreate(BaseModel):
    project_id: str
    name: str
    url: str
    target_type: str = "webpage"
    description: Optional[str] = None
    javascript_enabled: bool = True
    wait_for_selector: Optional[str] = None
    wait_time_ms: int = 0
    timeout_ms: int = 30000
    screenshot: bool = False
    headers: Optional[dict[str, str]] = None
    cookies: Optional[dict[str, str]] = None
    user_agent: Optional[str] = None
    extraction_strategy: Optional[str] = None
    extraction_config: Optional[dict] = None
    output_schema: Optional[dict] = None
    schedule_interval: Optional[str] = None
    tags: Optional[list[str]] = None


class TargetUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    javascript_enabled: Optional[bool] = None
    wait_for_selector: Optional[str] = None
    timeout_ms: Optional[int] = None
    screenshot: Optional[bool] = None
    headers: Optional[dict[str, str]] = None
    extraction_strategy: Optional[str] = None
    extraction_config: Optional[dict] = None
    output_schema: Optional[dict] = None
    tags: Optional[list[str]] = None


class TargetResponse(BaseModel):
    id: str
    project_id: str
    name: str
    url: str
    target_type: str
    description: Optional[str] = None
    is_active: bool
    javascript_enabled: bool
    timeout_ms: int
    created_at: Any
    updated_at: Any
    tags: Optional[list[str]] = None

    model_config = {"from_attributes": True}


@router.post("", response_model=TargetResponse, status_code=201)
async def create_target(
    target_data: TargetCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await verify_project_access(
        target_data.project_id, current_user["sub"], db, "member"
    )
    target = Target(
        project_id=target_data.project_id,
        name=target_data.name,
        url=target_data.url,
        target_type=TargetType(target_data.target_type),
        description=target_data.description,
        javascript_enabled=target_data.javascript_enabled,
        wait_for_selector=target_data.wait_for_selector,
        wait_time_ms=target_data.wait_time_ms,
        timeout_ms=target_data.timeout_ms,
        screenshot=target_data.screenshot,
        headers=target_data.headers,
        cookies=target_data.cookies,
        user_agent=target_data.user_agent,
        extraction_strategy=target_data.extraction_strategy,
        extraction_config=target_data.extraction_config,
        output_schema=target_data.output_schema,
        schedule_interval=target_data.schedule_interval,
        tags=target_data.tags,
        created_by=current_user.get("sub"),
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


@router.get("", response_model=list[TargetResponse])
async def list_targets(
    project_id: str = Query(...),
    is_active: Optional[bool] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await verify_project_access(project_id, current_user["sub"], db)
    query = select(Target).where(Target.project_id == project_id)
    if is_active is not None:
        query = query.where(Target.is_active == is_active)
    result = await db.execute(query.order_by(Target.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{target_id}", response_model=TargetResponse)
async def get_target(
    target_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    await verify_project_access(target.project_id, current_user["sub"], db)
    return target


@router.patch("/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: str,
    update_data: TargetUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    await verify_project_access(target.project_id, current_user["sub"], db, "member")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(target, key, value)
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{target_id}", status_code=204)
async def delete_target(
    target_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Target).where(Target.id == target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    await verify_project_access(target.project_id, current_user["sub"], db, "admin")
    await db.delete(target)
    await db.commit()
