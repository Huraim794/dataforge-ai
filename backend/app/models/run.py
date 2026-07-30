from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class RunStatus(str, enum.Enum):
    QUEUED = "queued"
    STARTING = "starting"
    NAVIGATING = "navigating"
    WAITING = "waiting"
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    CAPTCHA = "captcha"
    BLOCKED = "blocked"


class Run(TimestampMixin, Base):
    __tablename__ = "runs"

    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)

    url = Column(Text, nullable=False)
    status = Column(
        Enum(RunStatus), default=RunStatus.QUEUED, nullable=False, index=True
    )

    # Browser
    browser_type = Column(String(50), default="chromium")
    browser_context_id = Column(String(128), nullable=True)
    proxy_id = Column(String(36), ForeignKey("proxies.id"), nullable=True)
    user_agent = Column(String(512), nullable=True)
    viewport = Column(String(50), nullable=True)

    # Performance
    navigation_ms = Column(Integer, nullable=True)
    dom_content_loaded_ms = Column(Integer, nullable=True)
    total_time_ms = Column(Integer, nullable=True)
    page_size_bytes = Column(Integer, nullable=True)
    network_requests = Column(Integer, nullable=True)

    # Status codes
    http_status_code = Column(Integer, nullable=True)
    captcha_detected = Column(Boolean, default=False)
    captcha_solved = Column(Boolean, default=False)
    blocked_detected = Column(Boolean, default=False)
    cloudflare_detected = Column(Boolean, default=False)
    bot_score = Column(Integer, nullable=True)

    # Error
    error_message = Column(Text, nullable=True)
    error_type = Column(String(128), nullable=True)
    stack_trace = Column(Text, nullable=True)

    # Result
    screenshot_path = Column(String(512), nullable=True)
    pdf_path = Column(String(512), nullable=True)
    raw_content_path = Column(String(512), nullable=True)

    # Metadata
    worker_id = Column(String(128), nullable=True)
    queue_time_ms = Column(Integer, nullable=True)

    job = relationship("Job", back_populates="runs")
    pages = relationship(
        "Page", back_populates="run", cascade="all, delete-orphan", lazy="selectin"
    )
    proxy = relationship("Proxy", lazy="selectin")
