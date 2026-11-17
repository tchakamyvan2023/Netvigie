"""NETVIGIE — Modèle AgentWazuh (agents enregistrés dans Wazuh)."""
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from backend.models.base import Base, TimestampMixin, utcnow


class AgentWazuh(Base, TimestampMixin):
    __tablename__ = "agents_wazuh"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wazuh_id: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="any", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    os_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )