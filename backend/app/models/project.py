from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class ProjectMemberRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(Text, nullable=True)
    max_concurrent_jobs = Column(Integer, default=10)
    monthly_request_limit = Column(Integer, default=10000)
    storage_limit_mb = Column(Integer, default=1024)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    members = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    targets = relationship(
        "Target",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    jobs = relationship("Job", back_populates="project", lazy="dynamic")
    schedules = relationship("Schedule", back_populates="project", lazy="dynamic")
    proxies = relationship("Proxy", back_populates="project", lazy="selectin")


class ProjectMember(TimestampMixin, Base):
    __tablename__ = "project_members"

    project_id = Column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(
        Enum(ProjectMemberRole), default=ProjectMemberRole.MEMBER, nullable=False
    )

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="projects")
