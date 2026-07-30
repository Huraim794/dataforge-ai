from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataforge.backend.app.core.deps import get_current_user, get_db, verify_project_access
from pydantic import BaseModel

from dataforge.backend.app.models.schedule import Schedule, ScheduleInterval

router = APIRouter()


class ScheduleCreate(BaseModel):
    name: str
    project_id: str
    url: str
    interval: str = "daily"
    cron_expression: Optional[str] = None
    description: Optional[str] = None
    target_id: Optional[str] = None
    javascript_enabled: bool = True
    wait_for_selector: Optional[str] = None
    wait_time_ms: int = 0
    screenshot: bool = False
    max_retries: int = 3
    is_active: bool = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    max_runs: int = 0
    tags: Optional[list[str]] = None
    config: Optional[dict] = None


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    interval: Optional[str] = None
    cron_expression: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    max_runs: Optional[int] = None
    config: Optional[dict] = None


class ScheduleResponse(BaseModel):
    id: str
    project_id: str
    name: str
    url: str
    interval: str
    cron_expression: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    max_runs: int
    runs_so_far: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScheduleListResponse(BaseModel):
    items: list[ScheduleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


@router.post("", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    schedule_data: ScheduleCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await verify_project_access(schedule_data.project_id, current_user["sub"], db, "member")
    schedule = Schedule(
        project_id=schedule_data.project_id,
        name=schedule_data.name,
        url=schedule_data.url,
        interval=ScheduleInterval(schedule_data.interval),
        cron_expression=schedule_data.cron_expression,
        description=schedule_data.description,
        target_id=schedule_data.target_id,
        is_active=schedule_data.is_active,
        start_at=schedule_data.start_at,
        end_at=schedule_data.end_at,
        max_runs=schedule_data.max_runs,
        tags=schedule_data.tags,
        config=schedule_data.config or {},
        max_retries=schedule_data.max_retries,
        created_by=current_user.get("sub"),
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    from dataforge.backend.app.core.config import settings as app_settings
    if app_settings.scheduler_enabled:
        from dataforge.backend.app.main import job_scheduler
        if job_scheduler:
            await job_scheduler.add_schedule(schedule)

    return schedule


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    project_id: str = Query(...),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await verify_project_access(project_id, current_user["sub"], db)
    query = select(Schedule).where(Schedule.project_id == project_id)
    if is_active is not None:
        query = query.where(Schedule.is_active == is_active)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar()
    query = query.order_by(Schedule.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return ScheduleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
        has_next=(page * page_size) < total,
        has_prev=page > 1,
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await verify_project_access(schedule.project_id, current_user["sub"], db)
    return schedule


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    update_data: ScheduleUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await verify_project_access(schedule.project_id, current_user["sub"], db, "member")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if key == "interval":
            value = ScheduleInterval(value)
        setattr(schedule, key, value)
    await db.commit()
    await db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await verify_project_access(schedule.project_id, current_user["sub"], db, "admin")
    await db.delete(schedule)
    await db.commit()


@router.post("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await verify_project_access(schedule.project_id, current_user["sub"], db, "member")
    schedule.is_active = not schedule.is_active
    await db.commit()
    await db.refresh(schedule)
    return schedule
