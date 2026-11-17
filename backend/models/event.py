"""NETVIGIE — Modèle Event (événements normalisés)."""
from sqlalchemy import String, Text, DateTime, Integer, Float, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from backend.models.base import Base, TimestampMixin, utcnow


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    event_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    severity: Mapped[str] = mapped_column(String(32), default="info", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    machine_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    src_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    dst_ip: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    user: Mapped[str | None] = mapped_column(String(128), nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_events_ts_severity", "event_ts", "severity"),
    )