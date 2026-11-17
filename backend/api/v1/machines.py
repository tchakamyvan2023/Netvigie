"""
NETVIGIE — Endpoints Machines
GET /machines, GET /machines/{id}, GET /machines/{id}/metrics
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user, get_pagination
from backend.core.database import get_db
from backend.models.event import Event
from backend.models.machine import Machine
from backend.models.user import User
from backend.schemas.common import Page, PaginationParams
from backend.schemas.machine import MachineRead

router = APIRouter(prefix="/machines", tags=["machines"])


@router.get("", response_model=Page[MachineRead])
def list_machines(
    search: Optional[str] = Query(None, description="Recherche sur hostname ou IP"),
    status: Optional[str] = Query(None, description="active, disconnected, unknown"),
    excluded: Optional[bool] = Query(None, description="Filtrer les machines exclues"),
    pagination: PaginationParams = Depends(get_pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(Machine)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Machine.hostname.ilike(like), Machine.ip.ilike(like)))
    if status:
        q = q.filter(Machine.status == status)
    if excluded is not None:
        q = q.filter(Machine.is_excluded == excluded)

    total = q.count()
    items = (
        q.order_by(Machine.hostname)
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


@router.get("/{machine_id}", response_model=MachineRead)
def get_machine(
    machine_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Machine introuvable")
    return m


@router.get("/{machine_id}/metrics")
def get_machine_metrics(
    machine_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retourne l'historique des événements de type machine_metric."""
    m = db.query(Machine).filter(Machine.id == machine_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Machine introuvable")

    events = (
        db.query(Event)
        .filter(
            Event.machine_id == machine_id,
            Event.event_type == "machine_metric",
        )
        .order_by(desc(Event.event_ts))
        .limit(limit)
        .all()
    )

    return {
        "machine_id": machine_id,
        "hostname": m.hostname,
        "current": {
            "latency_ms": m.latency_ms,
            "packet_loss_percent": m.packet_loss_percent,
            "ram_usage_percent": m.ram_usage_percent,
            "last_ping_at": m.last_ping_at.isoformat() if m.last_ping_at else None,
        },
        "history": [
            {
                "ts": e.event_ts.isoformat(),
                "description": e.description,
            }
            for e in events
        ],
    }