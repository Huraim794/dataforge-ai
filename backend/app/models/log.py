from __future__ import annotations

import enum

from sqlalchemy import Column, Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Log(TimestampMixin, Base):
    __tablename__ = "logs"

    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=True, index=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=True, index=True)
    project_id = Column(
        String(36), ForeignKey("projects.id"), nullable=True, index=True
    )

    level = Column(Enum(LogLevel), default=LogLevel.INFO, nullable=False, index=True)
    source = Column(String(128), nullable=True, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)
    traceback = Column(Text, nullable=True)

    worker_id = Column(String(128), nullable=True)
    correlation_id = Column(String(36), nullable=True, index=True)

    job = relationship("Job", back_populates="logs")
