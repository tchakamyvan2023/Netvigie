"""NETVIGIE — Schémas Incident."""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class IncidentRead(BaseModel):
    id: int
    incident_id: str
    incident_ts: datetime
    verdict: str
    severity: str
    confidence: float
    status: str
    title: str
    description: Optional[str]
    primary_machine_id: Optional[int]
    evidence_json: Optional[Dict[str, Any]]
    recommendation: Optional[str]
    proposed_action: Optional[str]
    action_target: Optional[str]
    assigned_to: Optional[str]
    closed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class IncidentStatusUpdate(BaseModel):
    status: str
    resolution_notes: Optional[str] = None