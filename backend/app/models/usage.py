from __future__ import annotations


from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class UsageRecord(TimestampMixin, Base):
    __tablename__ = "usage_records"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(
        String(36), ForeignKey("projects.id"), nullable=True, index=True
    )

    action = Column(String(128), nullable=False, index=True)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(36), nullable=True)

    # Metrics
    requests_count = Column(Integer, default=1)
    pages_scraped = Column(Integer, default=0)
    bytes_processed = Column(Integer, default=0)
    ai_tokens_used = Column(Integer, default=0)
    ai_cost_usd = Column(Float, default=0.0)
    duration_ms = Column(Integer, default=0)

    # Billing
    billable = Column(Integer, default=1)
    credits_consumed = Column(Float, default=0.0)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    source = Column(String(64), nullable=True)
    metadata = Column(String(512), nullable=True)

    user = relationship("User", back_populates="usage")
    project = relationship("Project", lazy="selectin")
