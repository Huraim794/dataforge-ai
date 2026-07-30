from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class ProxyProtocol(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


class ProxyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BANNED = "banned"
    CHECKING = "checking"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


class Proxy(TimestampMixin, Base):
    __tablename__ = "proxies"

    project_id = Column(
        String(36), ForeignKey("projects.id"), nullable=True, index=True
    )

    host = Column(String(256), nullable=False, index=True)
    port = Column(Integer, nullable=False)
    protocol = Column(Enum(ProxyProtocol), default=ProxyProtocol.HTTP, nullable=False)
    username = Column(String(256), nullable=True)
    password = Column(String(512), nullable=True)

    status = Column(
        Enum(ProxyStatus), default=ProxyStatus.ACTIVE, nullable=False, index=True
    )
    is_shared = Column(Boolean, default=False)

    # Performance metrics
    latency_ms = Column(Float, nullable=True)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    ban_count = Column(Integer, default=0)
    total_requests = Column(Integer, default=0)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    last_banned_at = Column(DateTime(timezone=True), nullable=True)

    # Rate limiting
    requests_per_minute = Column(Integer, default=30)
    requests_this_minute = Column(Integer, default=0)
    minute_window_start = Column(DateTime(timezone=True), nullable=True)

    # Geo
    country = Column(String(100), nullable=True)
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    isp = Column(String(256), nullable=True)
    proxy_type = Column(String(50), nullable=True)
    anonymity_level = Column(String(50), nullable=True)

    # Scoring
    weight = Column(Float, default=1.0)
    score = Column(Float, default=1.0)
    source = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="proxies")
    jobs = relationship("Job", back_populates="proxy", lazy="dynamic")

    @property
    def url(self) -> str:
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.protocol.value}://{auth}{self.host}:{self.port}"

    @property
    def is_usable(self) -> bool:
        return (
            self.status == ProxyStatus.ACTIVE
            and self.consecutive_failures < 3
            and self.ban_count < 5
            and self.score > 0.3
        )
