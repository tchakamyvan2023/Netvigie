"""NETVIGIE — Schémas Agent (Wazuh + NETVIGIE)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AgentWazuhRead(BaseModel):
    id: int
    wazuh_id: str
    name: str
    ip: str
    status: str
    version: Optional[str] = None
    os_name: Optional[str] = None
    last_seen: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AgentNetvigieRead(BaseModel):
    id: int
    name: str
    status: str
    last_heartbeat: Optional[datetime] = None
    events_processed: int
    errors_count: int
    avg_processing_ms: float
    last_error: Optional[str] = None

    model_config = {"from_attributes": True}