from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class TargetType(str, enum.Enum):
    WEBPAGE = "webpage"
    API = "api"
    SPA = "spa"
    PDF = "pdf"
    IMAGE = "image"
    FEED = "feed"
    CUSTOM = "custom"


class Target(TimestampMixin, Base):
    __tablename__ = "targets"

    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    target_type = Column(Enum(TargetType), default=TargetType.WEBPAGE, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Scraping config
    javascript_enabled = Column(Boolean, default=True)
    wait_for_selector = Column(String(512), nullable=True)
    wait_time_ms = Column(Integer, default=0)
    timeout_ms = Column(Integer, default=30000)
    screenshot = Column(Boolean, default=False)
    pdf = Column(Boolean, default=False)
    headers = Column(JSON, nullable=True)
    cookies = Column(JSON, nullable=True)
    viewport_width = Column(Integer, default=1920)
    viewport_height = Column(Integer, default=1080)
    user_agent = Column(String(512), nullable=True)
    follow_redirects = Column(Boolean, default=True)
    max_depth = Column(Integer, default=1)
    include_patterns = Column(JSON, nullable=True)
    exclude_patterns = Column(JSON, nullable=True)

    # Extraction config
    extraction_strategy = Column(String(50), default="llm")
    extraction_config = Column(JSON, nullable=True)
    output_schema = Column(JSON, nullable=True)

    # Schedule
    schedule_interval = Column(String(50), nullable=True)
    schedule_cron = Column(String(100), nullable=True)

    # Metadata
    tags = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    project = relationship("Project", back_populates="targets")
    jobs = relationship("Job", back_populates="target", lazy="dynamic")
    schedules = relationship("Schedule", back_populates="target", lazy="dynamic")
