from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from dataforge.backend.app.core.deps import get_current_user, get_db, verify_project_access
from pydantic import BaseModel

from dataforge.backend.app.models.project import Project, ProjectMember, ProjectMemberRole

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[dict] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[dict] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_by: Optional[str] = None
    created_at: Any
    updated_at: Any

    model_config = {"from_attributes": True}


class ProjectDetailResponse(ProjectResponse):
    member_count: int = 0
    target_count: int = 0
    job_count: int = 0


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    project = Project(
        name=project_data.name,
        description=project_data.description,
        settings=project_data.settings,
        created_by=current_user.get("sub"),
    )
    db.add(project)
    await db.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=current_user.get("sub"),
        role=ProjectMemberRole.OWNER,
    )
    db.add(member)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    user_id = current_user.get("sub")
    result = await db.execute(
        select(Project).join(ProjectMember).where(
            ProjectMember.user_id == user_id,
            Project.is_active,
        )
    )
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await verify_project_access(project_id, current_user["sub"], db)
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    member_count_result = await db.execute(
        select(func.count(ProjectMember.id)).where(ProjectMember.project_id == project_id)
    )

    return {
        **project.__dict__,
        "member_count": member_count_result.scalar() or 0,
    }


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    update_data: ProjectUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    await verify_project_access(project_id, current_user["sub"], db, "admin")
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await verify_project_access(project_id, current_user["sub"], db, "owner")
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
