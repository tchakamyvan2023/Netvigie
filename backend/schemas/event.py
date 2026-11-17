"""NETVIGIE — Schémas Event."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EventRead(BaseModel):
    id: int
    event_id: str
    event_ts: datetime
    source: str
    event_type: str
    category: Optional[str]
    severity: str
    confidence: float
    machine_id: Optional[int]
    src_ip: Optional[str]
    dst_ip: Optional[str]
    user: Optional[str]
    description: Optional[str]

    model_config = {"from_attributes": True}