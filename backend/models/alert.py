"""NETVIGIE — Modèle Alert (alertes Wazuh)."""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin, utcnow


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    # --- Identifiants ---
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wazuh_alert_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    # --- Timestamp de l'alerte ---
    alert_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    # --- Règle Wazuh ---
    rule_id: Mapped[str | None] = mapped_column(
        String(32), index=True, nullable=True
    )
    rule_level: Mapped[int] = mapped_column(
        Integer, default=0, index=True, nullable=False
    )
    rule_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_groups: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Agent Wazuh ---
    agent_id: Mapped[str | None] = mapped_column(
        String(16), index=True, nullable=True
    )
    agent_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # --- Réseau ---
    src_ip: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    dst_ip: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    user: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # --- Contexte sécurité ---
    mitre_ids: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str] = mapped_column(
        String(32), default="low", index=True, nullable=False
    )
    full_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Champs d'analyse (Module 5) ---
    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    security_category: Mapped[str | None] = mapped_column(
        String(64), index=True, nullable=True
    )
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pattern_detected: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # --- Index composites (uniquement ceux non déclarés via index=True) ---
    __table_args__ = (
        Index("ix_alerts_ts_level", "alert_ts", "rule_level"),
    )