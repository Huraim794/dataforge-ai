from __future__ import annotations


from sqlalchemy import Column, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class ScrapeResult(TimestampMixin, Base):
    __tablename__ = "scrape_results"

    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=True, index=True)
    target_id = Column(String(36), ForeignKey("targets.id"), nullable=True, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)

    url = Column(Text, nullable=False)
    title = Column(String(512), nullable=True)
    status_code = Column(Integer, nullable=True)
    content_type = Column(String(256), nullable=True)
    content_length = Column(Integer, nullable=True)

    # Content
    raw_html = Column(Text, nullable=True)
    cleaned_text = Column(Text, nullable=True)
    markdown = Column(Text, nullable=True)
    screenshot_path = Column(String(512), nullable=True)
    pdf_path = Column(String(512), nullable=True)

    # Performance
    load_time_ms = Column(Float, nullable=True)
    ttfb_ms = Column(Float, nullable=True)
    dom_content_loaded_ms = Column(Float, nullable=True)
    network_requests = Column(Integer, nullable=True)
    page_size_bytes = Column(Integer, nullable=True)

    # Processed data
    links = Column(JSON, nullable=True)
    images = Column(JSON, nullable=True)
    structured_data = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)

    # Anti-bot
    captcha_detected = Column(Integer, default=0)
    captcha_solved = Column(Integer, default=0)
    blocked_detected = Column(Integer, default=0)
    bot_score = Column(Integer, nullable=True)

    # Status
    success = Column(Integer, default=0)

    # Error
    error_message = Column(Text, nullable=True)
    error_type = Column(String(128), nullable=True)

    job = relationship("Job", back_populates="scrape_results")
    run = relationship("Run", lazy="selectin")
    target = relationship("Target", lazy="selectin")
    project = relationship("Project", lazy="selectin")
    extractions = relationship("ExtractionResult", back_populates="scrape_result", cascade="all, delete-orphan", lazy="selectin")


class ExtractionResult(TimestampMixin, Base):
    __tablename__ = "extraction_results"

    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    run_id = Column(String(36), ForeignKey("runs.id"), nullable=True, index=True)
    scrape_result_id = Column(String(36), ForeignKey("scrape_results.id"), nullable=True, index=True)
    target_id = Column(String(36), ForeignKey("targets.id"), nullable=True, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=True, index=True)

    # Extraction data
    extracted_data = Column(JSON, nullable=True)
    structured_output = Column(JSON, nullable=True)
    raw_output = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # LLM info
    llm_provider = Column(String(64), nullable=True)
    llm_model = Column(String(128), nullable=True)
    tokens_prompt = Column(Integer, nullable=True)
    tokens_completion = Column(Integer, nullable=True)
    tokens_total = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)

    # Status
    success = Column(Integer, default=0)
    processing_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    extraction_strategy = Column(String(50), nullable=True)

    job = relationship("Job", back_populates="extraction_results")
    scrape_result = relationship("ScrapeResult", back_populates="extractions")
    run = relationship("Run", lazy="selectin")
    target = relationship("Target", lazy="selectin")
    project = relationship("Project", lazy="selectin")
