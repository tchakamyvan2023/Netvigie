"""
NETVIGIE — Service Événements
Normalise et stocke les événements (machines + alertes).
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.core.logging_config import setup_logging
from backend.models.event import Event

logger = setup_logging("netvigie.service.event")


def _new_event_id() -> str:
    return f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"


def create_event(
    db: Session,
    *,
    source: str,
    event_type: str,
    category: Optional[str] = None,
    severity: str = "info",
    confidence: float = 1.0,
    machine_id: Optional[int] = None,
    src_ip: Optional[str] = None,
    dst_ip: Optional[str] = None,
    user: Optional[str] = None,
    description: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
    event_ts: Optional[datetime] = None,
) -> Event:
    evt = Event(
        event_id=_new_event_id(),
        event_ts=event_ts or datetime.now(timezone.utc),
        source=source,
        event_type=event_type,
        category=category,
        severity=severity,
        confidence=confidence,
        machine_id=machine_id,
        src_ip=src_ip,
        dst_ip=dst_ip,
        user=user,
        description=description,
        raw_json=json.dumps(evidence or {}, default=str)[:60000],
    )
    db.add(evt)
    return evt


def event_from_alert(alert, machine_id: Optional[int] = None) -> Dict[str, Any]:
    """Transforme une alerte en dict d'événement."""
    return {
        "source": "wazuh",
        "event_type": "security_alert",
        "category": alert.rule_groups or "security",
        "severity": alert.severity,
        "confidence": min(alert.rule_level / 15.0, 1.0),
        "machine_id": machine_id,
        "src_ip": alert.src_ip,
        "dst_ip": alert.dst_ip,
        "user": alert.user,
        "description": alert.rule_description,
        "evidence": {
            "wazuh_alert_id": alert.wazuh_alert_id,
            "rule_id": alert.rule_id,
            "rule_level": alert.rule_level,
            "mitre_ids": alert.mitre_ids,
        },
        "event_ts": alert.alert_ts,
    }


def event_from_machine(machine) -> Dict[str, Any]:
    """Transforme une machine en dict d'événement (metric)."""
    return {
        "source": "collector",
        "event_type": "machine_metric",
        "category": "system",
        "severity": "info",
        "confidence": 1.0,
        "machine_id": machine.id,
        "src_ip": machine.ip,
        "dst_ip": None,
        "user": None,
        "description": (
            f"CPU {machine.ram_usage_percent or 0:.0f}% RAM, "
            f"OS {machine.os_name or '?'}"
        ),
        "evidence": {
            "agent_id": machine.agent_id,
            "hostname": machine.hostname,
            "cpu_cores": machine.cpu_cores,
            "ram_total_mb": machine.ram_total_mb,
            "ram_usage_percent": machine.ram_usage_percent,
            "status": machine.status,
        },
        "event_ts": datetime.now(timezone.utc),
    }