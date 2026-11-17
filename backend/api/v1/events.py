"""
NETVIGIE — Endpoints Événements
GET /events (filtres : source, type, sévérité, machine, période)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_pagination
from backend.core.database import get_db
from backend.models.event import Event
from backend.models.user import User
from backend.schemas.common import Page, PaginationParams
from backend.schemas.event import EventRead

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=Page[EventRead])
def list_events(
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    machine_id: Optional[int] = None,
    since_minutes: Optional[int] = Query(None, ge=1, le=10080),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Event)
    if source:
        q = q.filter(Event.source == source)
    if event_type:
        q = q.filter(Event.event_type == event_type)
    if severity:
        q = q.filter(Event.severity == severity)
    if machine_id:
        q = q.filter(Event.machine_id == machine_id)
    if since_minutes:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
        q = q.filter(Event.event_ts >= cutoff)

    total = q.count()
    items = (
        q.order_by(desc(Event.event_ts))
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