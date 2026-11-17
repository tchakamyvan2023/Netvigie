"""NETVIGIE — Schémas Statistiques."""
from typing import Dict, List
from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_machines: int
    active_machines: int
    unreachable_machines: int
    excluded_machines: int
    total_alerts: int
    alerts_last_hour: int
    critical_alerts: int
    total_incidents: int
    open_incidents: int
    incidents_by_verdict: Dict[str, int]
    incidents_by_severity: Dict[str, int]
    agents_status: Dict[str, str]
    wazuh_status: str


class TimeSeriesPoint(BaseModel):
    timestamp: str
    value: float


class TimeSeriesResponse(BaseModel):
    series: List[TimeSeriesPoint]
    metric: str
    period: str