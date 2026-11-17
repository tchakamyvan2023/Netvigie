"""NETVIGIE — Schémas Alert."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AlertRead(BaseModel):
    id: int
    wazuh_alert_id: str
    alert_ts: datetime
    rule_id: Optional[str]
    rule_level: int
    rule_description: Optional[str]
    agent_id: Optional[str]
    agent_name: Optional[str]
    src_ip: Optional[str]
    dst_ip: Optional[str]
    user: Optional[str]
    mitre_ids: Optional[str]
    severity: str

    model_config = {"from_attributes": True}