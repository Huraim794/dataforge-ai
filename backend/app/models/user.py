from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from dataforge.backend.app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    avatar_url = Column(String(512), nullable=True)
    company = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    preferences = Column(Text, nullable=True)

    projects = relationship("ProjectMember", back_populates="user", lazy="selectin")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    jobs = relationship("Job", back_populates="user", lazy="dynamic")
    usage = relationship("UsageRecord", back_populates="user", lazy="dynamic")


class APIKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(128), nullable=False, unique=True)
    key_prefix = Column(String(8), nullable=False)
    scopes = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    rate_limit_per_minute = Column(Integer, default=60)

    user = relationship("User", back_populates="api_keys")
