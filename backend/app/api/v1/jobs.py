from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataforge.backend.app.core.deps import (
    get_current_user,
    get_db,
    verify_project_access,
)
from dataforge.backend.app.models.job import Job, JobStatus
from dataforge.backend.app.models.project import ProjectMember
from dataforge.backend.app.models.run import Run
from pydantic import BaseModel, Field

from dataforge.backend.app.models.result import ExtractionResult, ScrapeResult

router = APIRouter()


class JobCreateRequest:
    pass


class JobCreate(BaseModel):
    url: str
    project_id: str
    target_id: Optional[str] = None
    priority: int = Field(default=5, ge=1, le=20)
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)
    wait_for_selector: Optional[str] = None
    wait_time_ms: int = Field(default=0, ge=0)
    javascript_enabled: bool = True
    screenshot: bool = False
    pdf: bool = False
    headers: Optional[dict[str, str]] = None
    cookies: Optional[dict[str, str]] = None
    user_agent: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


class JobResponse(BaseModel):
    id: str
    project_id: str
    url: str
    status: str
    priority: int
    retry_count: int
    max_retries: int
    duration_ms: int | None = None
    error_message: str | None = None
    error_type: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    tags: list[str] | None = None

    model_config = {"from_attributes": True}


class JobDetailResponse(JobResponse):
    runs: list[Any] = []
    scrape_results: list[Any] = []
    extraction_results: list[Any] = []


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class RunResponse(BaseModel):
    id: str
    job_id: str
    status: str
    attempt_number: int
    url: str
    browser_type: str | None = None
    navigation_ms: int | None = None
    total_time_ms: int | None = None
    http_status_code: int | None = None
    captcha_detected: bool = False
    blocked_detected: bool = False
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    job_data: JobCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await verify_project_access(job_data.project_id, current_user["sub"], db, "member")
    job = Job(
        project_id=job_data.project_id,
        url=job_data.url,
        target_id=job_data.target_id,
        priority=job_data.priority,
        max_retries=job_data.max_retries,
        timeout_ms=job_data.timeout_ms,
        wait_for_selector=job_data.wait_for_selector,
        wait_time_ms=job_data.wait_time_ms,
        javascript_enabled=job_data.javascript_enabled,
        screenshot=job_data.screenshot,
        pdf=job_data.pdf,
        headers=job_data.headers,
        cookies=job_data.cookies,
        user_agent=job_data.user_agent,
        tags=job_data.tags,
        metadata=job_data.metadata,
        status=JobStatus.PENDING,
        user_id=current_user.get("sub"),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = select(Job)

    if project_id:
        await verify_project_access(project_id, current_user["sub"], db)
        query = query.where(Job.project_id == project_id)
    else:
        user_project_ids = select(ProjectMember.project_id).where(
            ProjectMember.user_id == current_user["sub"]
        )
        query = query.where(Job.project_id.in_(user_project_ids))
    if status:
        query = query.where(Job.status == status)

    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar()
    query = (
        query.order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return JobListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
        has_next=(page * page_size) < total,
        has_prev=page > 1,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await verify_project_access(job.project_id, current_user["sub"], db)

    runs_result = await db.execute(
        select(Run).where(Run.job_id == job_id).order_by(Run.created_at.desc())
    )
    scraps_result = await db.execute(
        select(ScrapeResult)
        .where(ScrapeResult.job_id == job_id)
        .order_by(ScrapeResult.created_at.desc())
    )
    extractions_result = await db.execute(
        select(ExtractionResult)
        .where(ExtractionResult.job_id == job_id)
        .order_by(ExtractionResult.created_at.desc())
    )

    job_dict = {
        **job.__dict__,
        "runs": list(runs_result.scalars().all()),
        "scrape_results": list(scraps_result.scalars().all()),
        "extraction_results": list(extractions_result.scalars().all()),
    }
    return job_dict


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await verify_project_access(job.project_id, current_user["sub"], db, "member")
    if job.status in (JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.FAILED):
        raise HTTPException(
            status_code=400, detail=f"Job already in {job.status} state"
        )

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await verify_project_access(job.project_id, current_user["sub"], db, "member")
    job.status = JobStatus.PENDING
    job.retry_count = 0
    job.error_message = None
    job.error_type = None
    job.completed_at = None
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await verify_project_access(job.project_id, current_user["sub"], db, "admin")
    await db.delete(job)
    await db.commit()


@router.get("/{job_id}/runs", response_model=list[RunResponse])
async def get_job_runs(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await verify_project_access(job.project_id, current_user["sub"], db)
    runs_result = await db.execute(
        select(Run).where(Run.job_id == job_id).order_by(Run.created_at.desc())
    )
    return list(runs_result.scalars().all())


@router.get("/{job_id}/results")
async def get_job_results(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await verify_project_access(job.project_id, current_user["sub"], db)
    scrape_result = await db.execute(
        select(ScrapeResult)
        .where(ScrapeResult.job_id == job_id)
        .order_by(ScrapeResult.created_at.desc())
    )
    scrape_results = list(scrape_result.scalars().all())

    extraction_result = await db.execute(
        select(ExtractionResult)
        .where(ExtractionResult.job_id == job_id)
        .order_by(ExtractionResult.created_at.desc())
    )
    extraction_results = list(extraction_result.scalars().all())

    return {
        "scrape_results": [
            {
                "id": r.id,
                "url": r.url,
                "title": r.title,
                "status_code": r.status_code,
                "cleaned_text": r.cleaned_text[:5000] if r.cleaned_text else None,
                "load_time_ms": r.load_time_ms,
                "captcha_detected": r.captcha_detected,
                "blocked_detected": r.blocked_detected,
                "links": r.links,
                "created_at": r.created_at,
            }
            for r in scrape_results
        ],
        "extraction_results": [
            {
                "id": r.id,
                "extracted_data": r.extracted_data,
                "structured_output": r.structured_output,
                "confidence_score": r.confidence_score,
                "llm_model": r.llm_model,
                "tokens_total": r.tokens_total,
                "success": r.success,
                "created_at": r.created_at,
            }
            for r in extraction_results
        ],
    }
