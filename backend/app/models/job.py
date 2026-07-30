from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    CAPTCHA_REQUIRED = "captcha_required"


class JobPriority(int, enum.Enum):
    LOW = 1
    MEDIUM = 5
    HIGH = 10
    CRITICAL = 20


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    target_id = Column(String(36), ForeignKey("targets.id"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    schedule_id = Column(String(36), ForeignKey("schedules.id"), nullable=True, index=True)
    proxy_id = Column(String(36), ForeignKey("proxies.id"), nullable=True, index=True)

    url = Column(Text, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    priority = Column(Integer, default=JobPriority.MEDIUM.value, nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    timeout_ms = Column(Integer, default=30000)

    # Configuration snapshot
    config = Column(JSON, nullable=True)
    headers = Column(JSON, nullable=True)
    cookies = Column(JSON, nullable=True)
    javascript_enabled = Column(Boolean, default=True)
    wait_for_selector = Column(String(512), nullable=True)
    wait_time_ms = Column(Integer, default=0)
    screenshot = Column(Boolean, default=False)
    pdf = Column(Boolean, default=False)
    user_agent = Column(String(512), nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    queued_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Results
    duration_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    error_type = Column(String(128), nullable=True)

    # Metadata
    tags = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    is_recurring = Column(Boolean, default=False)

    project = relationship("Project", back_populates="jobs")
    target = relationship("Target", back_populates="jobs")
    user = relationship("User", back_populates="jobs")
    schedule = relationship("Schedule", back_populates="jobs")
    proxy = relationship("Proxy", back_populates="jobs")
    runs = relationship("Run", back_populates="job", cascade="all, delete-orphan", lazy="selectin")
    scrape_results = relationship("ScrapeResult", back_populates="job", cascade="all, delete-orphan", lazy="selectin")
    extraction_results = relationship("ExtractionResult", back_populates="job", cascade="all, delete-orphan", lazy="selectin")
    logs = relationship("Log", back_populates="job", lazy="dynamic")
