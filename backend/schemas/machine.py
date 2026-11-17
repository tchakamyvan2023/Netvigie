"""NETVIGIE — Schémas Machine."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MachineRead(BaseModel):
    id: int
    agent_id: Optional[str]
    hostname: str
    ip: str
    os_name: Optional[str]
    os_version: Optional[str]
    kernel: Optional[str]
    cpu_name: Optional[str]
    cpu_cores: Optional[int]
    ram_total_mb: Optional[int]
    ram_usage_percent: Optional[float]
    disk_usage_percent: Optional[float]
    latency_ms: Optional[float]
    packet_loss_percent: Optional[float]
    status: str
    is_excluded: bool
    role: Optional[str]
    criticality: Optional[str]
    display_name: Optional[str]
    last_seen: Optional[datetime]
    last_sync: datetime

    model_config = {"from_attributes": True}