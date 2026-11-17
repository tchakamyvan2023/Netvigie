"""
NETVIGIE — Service Diagnostic
Mesure la latence et les pertes via ICMP, compare aux seuils,
met à jour la base, produit un Diagnostic normalisé.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.core.config import netvigie_config
from backend.core.logging_config import setup_logging
from backend.core.network import PingResult, ping
from backend.models.machine import Machine

logger = setup_logging("netvigie.service.diagnostic")


# Statuts possibles
STATUS_NORMAL = "NORMAL"
STATUS_ANOMALY = "ANOMALY"
STATUS_UNREACHABLE = "UNREACHABLE"


def _thresholds() -> Dict[str, Any]:
    """Retourne les seuils configurés dans config/netvigie.yaml."""
    return netvigie_config.thresholds


def diagnose_machine(machine: Machine, ping_timeout_s: int = 2) -> Dict[str, Any]:
    """
    Diagnostique une machine : ping ICMP + comparaison aux seuils.
    
    Args:
        machine: Instance Machine (avec .ip, .hostname, .id, .agent_id)
        ping_timeout_s: Timeout par paquet (secondes)
    
    Returns:
        Dict Diagnostic avec status, latency_ms, packet_loss_percent, thresholds, ts.
    """
    thresholds = _thresholds()
    latency_threshold = float(thresholds.get("latency_ms", 300))
    loss_threshold = float(thresholds.get("packet_loss_percent", 3.0))

    result: PingResult = ping(machine.ip, count=4, timeout_s=ping_timeout_s)

    # Déterminer le statut
    if not result.reachable:
        status = STATUS_UNREACHABLE
    else:
        is_anomaly = False
        if result.latency_ms is not None and result.latency_ms > latency_threshold:
            is_anomaly = True
        if result.packet_loss_percent > loss_threshold:
            is_anomaly = True
        status = STATUS_ANOMALY if is_anomaly else STATUS_NORMAL

    # Construire le diagnostic
    diagnostic = {
        "machine_id": machine.id,
        "hostname": machine.hostname,
        "ip": machine.ip,
        "agent_id": machine.agent_id,
        "status": status,
        "latency_ms": result.latency_ms,
        "packet_loss_percent": result.packet_loss_percent,
        "packets_sent": result.packets_sent,
        "packets_received": result.packets_received,
        "thresholds": {
            "latency_ms": latency_threshold,
            "packet_loss_percent": loss_threshold,
        },
        "ts": datetime.now(timezone.utc).timestamp(),
        "diagnosed_at": datetime.now(timezone.utc).isoformat(),
    }

    return diagnostic


def update_machine_network(
    db: Session,
    machine_id: int,
    diagnostic: Dict[str, Any],
) -> Optional[Machine]:
    """
    Met à jour les colonnes réseau de la machine.
    Retourne la machine mise à jour, ou None si introuvable.
    """
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        return None
    machine.latency_ms = diagnostic.get("latency_ms")
    machine.packet_loss_percent = diagnostic.get("packet_loss_percent")
    machine.last_ping_at = datetime.now(timezone.utc)
    return machine


def is_anomaly(diagnostic: Dict[str, Any]) -> bool:
    """Retourne True si le diagnostic est ANOMALY ou UNREACHABLE."""
    return diagnostic.get("status") in (STATUS_ANOMALY, STATUS_UNREACHABLE)