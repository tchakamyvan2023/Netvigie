"""NETVIGIE — Modèle Incident (verdicts de l'Agent 04)."""
from sqlalchemy import String, Text, DateTime, Integer, Float, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from backend.models.base import Base, TimestampMixin, utcnow


# Verdicts possibles (section 4 du cahier des charges)
VERDICTS = {
    "NORMAL",
    "TECHNICAL_ANOMALY",
    "NETWORK_FAILURE",
    "SECURITY_ALERT",
    "SUSPECTED_ATTACK",
    "MIXED_INCIDENT",
    "INVESTIGATION_REQUIRED",
}

STATUSES = {"new", "acknowledged", "investigating", "resolved", "false_positive"}


class Incident(Base, TimestampMixin):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    incident_ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )

    verdict: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True, nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    primary_machine_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    machine_ids_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    event_ids_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    alert_ids_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_action: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action_target: Mapped[str | None] = mapped_column(String(128), nullable=True)

    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_incidents_ts_verdict", "incident_ts", "verdict"),
        Index("ix_incidents_status_severity", "status", "severity"),
    )