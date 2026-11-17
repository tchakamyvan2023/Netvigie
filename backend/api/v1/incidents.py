"""
NETVIGIE — Endpoints Incidents
GET /incidents, GET /incidents/{id}, PATCH /incidents/{id}/status
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_pagination, require_permission
from backend.core.database import get_db
from backend.models.audit_log import AuditLog
from backend.models.incident import STATUSES, Incident
from backend.models.user import User
from backend.schemas.common import Page, PaginationParams
from backend.schemas.incident import IncidentRead, IncidentStatusUpdate

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=Page[IncidentRead])
def list_incidents(
    verdict: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    since_minutes: Optional[int] = Query(None, ge=1, le=43200),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Incident)
    if verdict:
        q = q.filter(Incident.verdict == verdict)
    if severity:
        q = q.filter(Incident.severity == severity)
    if status:
        q = q.filter(Incident.status == status)
    if since_minutes:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
        q = q.filter(Incident.incident_ts >= cutoff)

    total = q.count()
    items = (
        q.order_by(desc(Incident.incident_ts))
        .offset(pagination.offset)
        .limit(pagination.page_size)
        .all()
    )
    return Page(
        items=items,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size,
    )


@router.get("/{incident_id}", response_model=IncidentRead)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident introuvable")
    return inc


@router.patch("/{incident_id}/status", response_model=IncidentRead)
def update_incident_status(
    incident_id: int,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("can_manage_incidents")),
):
    if payload.status not in STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Statut invalide. Valeurs autorisées : {sorted(STATUSES)}",
        )
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident introuvable")

    inc.status = payload.status
    if payload.resolution_notes:
        inc.resolution_notes = payload.resolution_notes
    if payload.status in ("resolved", "false_positive"):
        inc.closed_at = datetime.now(timezone.utc)
        inc.closed_by = user.username

    db.add(AuditLog(
        actor=user.username,
        action="incident_status_update",
        target=inc.incident_id,
        result="ok",
        details=f"{payload.status} — {payload.resolution_notes or ''}"[:500],
    ))
    db.commit()
    db.refresh(inc)
    return inc