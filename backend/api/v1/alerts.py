"""
NETVIGIE — Endpoints Alertes
GET /alerts (filtres : agent, niveau, sévérité, catégorie)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_pagination
from backend.core.database import get_db
from backend.models.alert import Alert
from backend.models.user import User
from backend.schemas.alert import AlertRead
from backend.schemas.common import Page, PaginationParams

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=Page[AlertRead])
def list_alerts(
    agent_id: Optional[str] = None,
    min_level: Optional[int] = Query(None, ge=0, le=16),
    severity: Optional[str] = None,
    category: Optional[str] = None,
    since_minutes: Optional[int] = Query(None, ge=1, le=10080),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Alert)
    if agent_id:
        q = q.filter(Alert.agent_id == agent_id)
    if min_level is not None:
        q = q.filter(Alert.rule_level >= min_level)
    if severity:
        q = q.filter(Alert.severity == severity)
    if category:
        q = q.filter(Alert.security_category == category)
    if since_minutes:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
        q = q.filter(Alert.alert_ts >= cutoff)

    total = q.count()
    items = (
        q.order_by(desc(Alert.alert_ts))
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