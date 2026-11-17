"""NETVIGIE — Modèle AgentNetvigie (état des 4 agents NETVIGIE)."""
from sqlalchemy import String, Integer, Float, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from backend.models.base import Base, TimestampMixin, utcnow


class AgentNetvigie(Base, TimestampMixin):
    __tablename__ = "agents_netvigie"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="stopped", nullable=False)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    events_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_processing_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)