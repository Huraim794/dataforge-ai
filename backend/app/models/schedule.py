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


class ScheduleInterval(str, enum.Enum):
    ONCE = "once"
    EVERY_MINUTE = "every_minute"
    EVERY_5_MINUTES = "every_5_minutes"
    EVERY_15_MINUTES = "every_15_minutes"
    EVERY_30_MINUTES = "every_30_minutes"
    HOURLY = "hourly"
    EVERY_2_HOURS = "every_2_hours"
    EVERY_4_HOURS = "every_4_hours"
    EVERY_6_HOURS = "every_6_hours"
    EVERY_12_HOURS = "every_12_hours"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    CUSTOM_CRON = "custom_cron"


class Schedule(TimestampMixin, Base):
    __tablename__ = "schedules"

    project_id = Column(
        String(36), ForeignKey("projects.id"), nullable=False, index=True
    )
    target_id = Column(String(36), ForeignKey("targets.id"), nullable=True, index=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    interval = Column(
        Enum(ScheduleInterval), default=ScheduleInterval.DAILY, nullable=False
    )
    cron_expression = Column(String(100), nullable=True)

    url = Column(Text, nullable=False)
    config = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    max_runs = Column(Integer, default=0)
    runs_so_far = Column(Integer, default=0)

    max_retries = Column(Integer, default=3)
    notify_on_failure = Column(Boolean, default=True)
    notification_email = Column(String(255), nullable=True)

    metadata = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="schedules")
    target = relationship("Target", back_populates="schedules")
    jobs = relationship("Job", back_populates="schedule", lazy="dynamic")
