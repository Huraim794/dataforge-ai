from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    get_current_user,
    get_db,
    require_role,
    verify_project_access,
)
from app.models.proxy import Proxy, ProxyProtocol, ProxyStatus
from pydantic import BaseModel, Field

from app.proxy.checker import ProxyChecker

router = APIRouter()
checker = ProxyChecker()


class ProxyCreate:
    pass


class ProxyCreateSchema(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    project_id: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    proxy_type: Optional[str] = None
    anonymity_level: Optional[str] = None
    weight: float = Field(default=1.0, ge=0.1, le=10.0)
    source: Optional[str] = None
    notes: Optional[str] = None


class ProxyResponse(BaseModel):
    id: str
    host: str
    port: int
    protocol: str
    status: str
    username: Optional[str] = None
    latency_ms: Optional[float] = None
    success_count: int
    failure_count: int
    consecutive_failures: int
    ban_count: int
    total_requests: int
    country: Optional[str] = None
    isp: Optional[str] = None
    anonymity_level: Optional[str] = None
    weight: float
    score: float
    is_usable: bool
    url: str
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class ProxyListResponse(BaseModel):
    items: list[ProxyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


@router.post("", response_model=ProxyResponse, status_code=201)
async def create_proxy(
    proxy_data: ProxyCreateSchema,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    if proxy_data.project_id:
        await verify_project_access(
            proxy_data.project_id, current_user["sub"], db, "member"
        )
    proxy = Proxy(
        host=proxy_data.host,
        port=proxy_data.port,
        protocol=ProxyProtocol(proxy_data.protocol),
        username=proxy_data.username,
        password=proxy_data.password,
        project_id=proxy_data.project_id,
        country=proxy_data.country,
        region=proxy_data.region,
        city=proxy_data.city,
        isp=proxy_data.isp,
        proxy_type=proxy_data.proxy_type,
        anonymity_level=proxy_data.anonymity_level,
        weight=proxy_data.weight,
        source=proxy_data.source,
        notes=proxy_data.notes,
    )
    db.add(proxy)
    await db.commit()
    await db.refresh(proxy)
    return proxy


@router.get("", response_model=ProxyListResponse)
async def list_proxies(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    query = select(Proxy)

    if project_id:
        await verify_project_access(project_id, current_user["sub"], db)
        query = query.where(Proxy.project_id == project_id)
    if status:
        query = query.where(Proxy.status == ProxyStatus(status))
    if country:
        query = query.where(Proxy.country == country)

    total = (
        await db.execute(select(func.count()).select_from(query.subquery()))
    ).scalar()
    query = (
        query.order_by(Proxy.score.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return ProxyListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, (total + page_size - 1) // page_size),
        has_next=(page * page_size) < total,
        has_prev=page > 1,
    )


@router.get("/{proxy_id}", response_model=ProxyResponse)
async def get_proxy(
    proxy_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Proxy).where(Proxy.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    if proxy.project_id:
        await verify_project_access(proxy.project_id, current_user["sub"], db)
    return proxy


@router.delete("/{proxy_id}", status_code=204)
async def delete_proxy(
    proxy_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Proxy).where(Proxy.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    if proxy.project_id:
        await verify_project_access(proxy.project_id, current_user["sub"], db, "admin")
    await db.delete(proxy)
    await db.commit()


@router.post("/{proxy_id}/check")
async def check_proxy(
    proxy_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(select(Proxy).where(Proxy.id == proxy_id))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise HTTPException(status_code=404, detail="Proxy not found")
    if proxy.project_id:
        await verify_project_access(proxy.project_id, current_user["sub"], db, "member")

    check_result = await checker.check_proxy(
        host=proxy.host,
        port=proxy.port,
        protocol=proxy.protocol.value,
        username=proxy.username,
        password=proxy.password,
    )

    proxy.latency_ms = check_result.get("latency_ms")
    proxy.last_checked_at = datetime.now(timezone.utc)
    if check_result.get("alive"):
        proxy.status = ProxyStatus.ACTIVE
        proxy.country = check_result.get("country") or proxy.country
    else:
        proxy.consecutive_failures += 1
        if proxy.consecutive_failures >= 3:
            proxy.status = ProxyStatus.INACTIVE
    await db.commit()
    await db.refresh(proxy)

    return {**check_result, "proxy": proxy}


@router.post("/check-all")
async def check_all_proxies(
    current_user: dict = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    result = await db.execute(
        select(Proxy).where(
            Proxy.status.in_([ProxyStatus.ACTIVE, ProxyStatus.INACTIVE])
        )
    )
    proxies = list(result.scalars().all())

    batch = [
        {
            "id": p.id,
            "host": p.host,
            "port": p.port,
            "protocol": p.protocol.value,
            "username": p.username,
            "password": p.password,
        }
        for p in proxies
    ]

    results = await checker.check_proxy_batch(batch, concurrency=20)
    alive = sum(1 for r in results if r.get("alive"))
    dead = len(results) - alive

    return {
        "total": len(results),
        "alive": alive,
        "dead": dead,
        "results": results,
    }
