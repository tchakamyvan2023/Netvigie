"""NETVIGIE — Modèle Machine (supervisée via syscollector)."""
from sqlalchemy import String, Integer, Float, DateTime, Text, Boolean, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from backend.models.base import Base, TimestampMixin, utcnow


class Machine(Base, TimestampMixin):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    hostname: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    ip: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # OS
    os_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kernel: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Hardware
    cpu_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_mhz: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_total_mb: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ram_free_mb: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ram_usage_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_total_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_free_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_usage_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Réseau
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_ping_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # État
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    criticality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Dernières communications
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)