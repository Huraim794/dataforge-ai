from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import declared_attr


class TimestampMixin:
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
