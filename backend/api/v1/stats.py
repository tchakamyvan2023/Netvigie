"""
NETVIGIE — Endpoints Statistiques
GET /stats/overview, GET /stats/timeseries
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.models.agent_netvigie import AgentNetvigie
from backend.models.alert import Alert
from backend.models.event import Event
from backend.models.incident import Incident
from backend.models.machine import Machine
from backend.models.user import User
from backend.schemas.stats import OverviewStats, TimeSeriesPoint, TimeSeriesResponse

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=OverviewStats)
def overview(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    total_machines = db.query(func.count(Machine.id)).scalar() or 0

    active = (
        db.query(func.count(Machine.id))
        .filter(Machine.status == "active", Machine.is_excluded == False)  # noqa: E712
        .scalar() or 0
    )

    unreachable = (
        db.query(func.count(Machine.id))
        .filter(Machine.latency_ms.is_(None), Machine.is_excluded == False)  # noqa: E712
        .scalar() or 0
    )

    excluded = (
        db.query(func.count(Machine.id))
        .filter(Machine.is_excluded == True)  # noqa: E712
        .scalar() or 0
    )

    total_alerts = db.query(func.count(Alert.id)).scalar() or 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    alerts_last_hour = (
        db.query(func.count(Alert.id))
        .filter(Alert.alert_ts >= cutoff)
        .scalar() or 0
    )

    critical_alerts = (
        db.query(func.count(Alert.id))
        .filter(Alert.rule_level >= 12)
        .scalar() or 0
    )

    total_inc = db.query(func.count(Incident.id)).scalar() or 0

    open_inc = (
        db.query(func.count(Incident.id))
        .filter(Incident.status.in_(["new", "acknowledged", "investigating"]))
        .scalar() or 0
    )

    by_verdict = dict(
        db.query(Incident.verdict, func.count(Incident.id))
        .group_by(Incident.verdict)
        .all()
    )

    by_severity = dict(
        db.query(Incident.severity, func.count(Incident.id))
        .group_by(Incident.severity)
        .all()
    )

    agents_status = dict(
        db.query(AgentNetvigie.name, AgentNetvigie.status).all()
    )

    return OverviewStats(
        total_machines=total_machines,
        active_machines=active,
        unreachable_machines=unreachable,
        excluded_machines=excluded,
        total_alerts=total_alerts,
        alerts_last_hour=alerts_last_hour,
        critical_alerts=critical_alerts,
        total_incidents=total_inc,
        open_incidents=open_inc,
        incidents_by_verdict=by_verdict,
        incidents_by_severity=by_severity,
        agents_status=agents_status,
        wazuh_status="ok" if settings.wazuh_api_url else "unknown",
    )


@router.get("/timeseries", response_model=TimeSeriesResponse)
def timeseries(
    metric: str = Query("events", description="events | alerts | incidents"),
    period_minutes: int = Query(60, ge=5, le=1440),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=period_minutes)

    if metric == "events":
        rows = (
            db.query(
                func.date_trunc("minute", Event.event_ts).label("bucket"),
                func.count(Event.id),
            )
            .filter(Event.event_ts >= cutoff)
            .group_by("bucket")
            .order_by("bucket")
            .all()
        )
    elif metric == "alerts":
        rows = (
            db.query(
                func.date_trunc("minute", Alert.alert_ts).label("bucket"),
                func.count(Alert.id),
            )
            .filter(Alert.alert_ts >= cutoff)
            .group_by("bucket")
            .order_by("bucket")
            .all()
        )
    elif metric == "incidents":
        rows = (
            db.query(
                func.date_trunc("minute", Incident.incident_ts).label("bucket"),
                func.count(Incident.id),
            )
            .filter(Incident.incident_ts >= cutoff)
            .group_by("bucket")
            .order_by("bucket")
            .all()
        )
    else:
        rows = []

    series = [
        TimeSeriesPoint(timestamp=ts.isoformat(), value=float(count))
        for ts, count in rows
    ]
    return TimeSeriesResponse(series=series, metric=metric, period=f"{period_minutes}m")