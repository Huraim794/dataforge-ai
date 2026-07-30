from __future__ import annotations


from sqlalchemy import Column, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class Page(TimestampMixin, Base):
    __tablename__ = "pages"

    run_id = Column(String(36), ForeignKey("runs.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(String(512), nullable=True)
    depth = Column(Integer, default=0)

    # Content
    raw_html = Column(Text, nullable=True)
    cleaned_text = Column(Text, nullable=True)
    markdown = Column(Text, nullable=True)
    text_length = Column(Integer, nullable=True)

    # Metadata
    status_code = Column(Integer, nullable=True)
    content_type = Column(String(256), nullable=True)
    content_length = Column(Integer, nullable=True)
    load_time_ms = Column(Integer, nullable=True)
    headers = Column(JSON, nullable=True)

    # Extracted data
    links = Column(JSON, nullable=True)
    images = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    structured_data = Column(JSON, nullable=True)

    # AI
    ai_summary = Column(Text, nullable=True)
    ai_analysis = Column(JSON, nullable=True)
    ai_classification = Column(JSON, nullable=True)

    run = relationship("Run", back_populates="pages")
