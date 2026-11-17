"""
NETVIGIE — Service Corrélation
Applique la table de décision 2×2 avec précédence temporelle.
Produit un verdict parmi 7 et crée les incidents.

Corrections :
- Ajout de incident_exists_recent() pour éviter les doublons
- Fenêtre de déduplication configurable (5 min par défaut)
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.core.config import netvigie_config
from backend.core.logging_config import setup_logging
from backend.models.incident import Incident

logger = setup_logging("netvigie.service.correlation")


# ---------------------------------------------------------------------------
# Verdicts possibles
# ---------------------------------------------------------------------------
VERDICT_NORMAL = "NORMAL"
VERDICT_TECHNICAL_ANOMALY = "TECHNICAL_ANOMALY"
VERDICT_NETWORK_FAILURE = "NETWORK_FAILURE"
VERDICT_SECURITY_ALERT = "SECURITY_ALERT"
VERDICT_SUSPECTED_ATTACK = "SUSPECTED_ATTACK"
VERDICT_MIXED_INCIDENT = "MIXED_INCIDENT"
VERDICT_INVESTIGATION_REQUIRED = "INVESTIGATION_REQUIRED"

ALL_VERDICTS = {
    VERDICT_NORMAL,
    VERDICT_TECHNICAL_ANOMALY,
    VERDICT_NETWORK_FAILURE,
    VERDICT_SECURITY_ALERT,
    VERDICT_SUSPECTED_ATTACK,
    VERDICT_MIXED_INCIDENT,
    VERDICT_INVESTIGATION_REQUIRED,
}

# Seuil "attaque suspectée" (niveau Wazuh)
SUSPECTED_ATTACK_LEVEL = 12

# Fenêtre de déduplication par défaut (minutes)
DEDUP_WINDOW_MINUTES = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _new_incident_id() -> str:
    return f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"


def _precedence_ok(
    security_ts: float,
    network_ts: float,
    threshold_ms: int,
) -> bool:
    """Vérifie que la sécurité précède le réseau (delta <= -threshold_ms)."""
    delta_ms = (security_ts - network_ts) * 1000
    return delta_ms <= -threshold_ms


# ---------------------------------------------------------------------------
# Décision (table 2×2 + précédence temporelle)
# ---------------------------------------------------------------------------
def decide_verdict(
    diagnostic: Optional[Dict[str, Any]],
    assessment: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Applique la table de décision 2×2.
    Retourne un dict avec verdict, severity, confidence, evidence, description.
    """
    correlation_cfg = netvigie_config.correlation
    precedence_threshold = int(correlation_cfg.get("precedence_threshold_ms", 200))
    min_confidence = float(correlation_cfg.get("min_confidence_for_incident", 0.5))

    # Extraire les statuts
    network_status = (diagnostic or {}).get("status", "NORMAL")
    security_category = (assessment or {}).get("category")
    security_level = (assessment or {}).get("rule_level", 0)
    security_risk = (assessment or {}).get("risk_score", 0.0)
    security_is_brute = (assessment or {}).get("is_brute_force", False)
    security_is_scan = (assessment or {}).get("is_port_scan", False)

    network_anomaly = network_status in ("ANOMALY", "UNREACHABLE")
    security_alert = bool(security_category)
    security_suspected = security_level >= SUSPECTED_ATTACK_LEVEL or security_is_brute

    # Cas 1 : tout NORMAL
    if not network_anomaly and not security_alert:
        return {
            "verdict": VERDICT_NORMAL,
            "severity": "info",
            "confidence": 1.0,
            "description": "Aucune anomalie réseau ni alerte de sécurité",
            "evidence": {},
        }

    # Cas 2 : réseau anormal, sécurité normale
    if network_anomaly and not security_alert:
        if network_status == "UNREACHABLE":
            verdict = VERDICT_NETWORK_FAILURE
            description = "Machine injoignable (panne réseau ou service arrêté)"
            confidence = 0.9
        else:
            verdict = VERDICT_TECHNICAL_ANOMALY
            description = "Anomalie réseau détectée sans alerte de sécurité"
            confidence = 0.8
        return {
            "verdict": verdict,
            "severity": "high",
            "confidence": confidence,
            "description": description,
            "evidence": {
                "diagnostic": diagnostic,
                "assessment": None,
            },
        }

    # Cas 3 : réseau normal, sécurité suspecte
    if not network_anomaly and security_alert:
        if security_suspected:
            verdict = VERDICT_SUSPECTED_ATTACK
            description = f"Attaque suspectée : {security_category} (niveau {security_level})"
            confidence = 0.9
            severity = "critical"
        else:
            verdict = VERDICT_SECURITY_ALERT
            description = f"Alerte de sécurité : {security_category} (niveau {security_level})"
            confidence = 0.85
            severity = "high"
        return {
            "verdict": verdict,
            "severity": severity,
            "confidence": confidence,
            "description": description,
            "evidence": {
                "diagnostic": None,
                "assessment": assessment,
            },
        }

    # Cas 4 : réseau anormal ET sécurité suspecte -> MIXED ou INVESTIGATION
    if network_anomaly and security_alert:
        network_ts = (diagnostic or {}).get("ts", 0)
        security_ts = (assessment or {}).get("alert_ts", 0)

        if _precedence_ok(security_ts, network_ts, precedence_threshold):
            verdict = VERDICT_MIXED_INCIDENT
            description = (
                f"Incident mixte : la lenteur réseau vient de l'attaque "
                f"({security_category})"
            )
            confidence = 0.85
            severity = "critical"
        else:
            verdict = VERDICT_INVESTIGATION_REQUIRED
            description = (
                f"Anomalie réseau et alerte sécurité simultanées "
                f"({security_category}) — précédence incertaine"
            )
            confidence = 0.5
            severity = "high"

        return {
            "verdict": verdict,
            "severity": severity,
            "confidence": max(confidence, min_confidence),
            "description": description,
            "evidence": {
                "diagnostic": diagnostic,
                "assessment": assessment,
                "delta_ms": (security_ts - network_ts) * 1000,
                "precedence_threshold_ms": precedence_threshold,
            },
        }

    # Fallback
    return {
        "verdict": VERDICT_INVESTIGATION_REQUIRED,
        "severity": "medium",
        "confidence": 0.3,
        "description": "État indéterminé — investigation manuelle requise",
        "evidence": {"diagnostic": diagnostic, "assessment": assessment},
    }


# ---------------------------------------------------------------------------
# Déduplication : vérifier si un incident récent identique existe déjà
# ---------------------------------------------------------------------------
def incident_exists_recent(
    db: Session,
    machine_id: Optional[int],
    verdict: str,
    window_minutes: int = DEDUP_WINDOW_MINUTES,
) -> bool:
    """
    Vérifie si un incident identique (même machine, même verdict)
    existe déjà dans les N dernières minutes et n'est pas fermé.

    Évite les doublons à chaque itération de l'Agent Correlation
    (qui tourne toutes les 20s).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    query = db.query(Incident).filter(
        Incident.verdict == verdict,
        Incident.incident_ts >= cutoff,
        Incident.status.in_(["new", "acknowledged", "investigating"]),
    )
    if machine_id is not None:
        query = query.filter(Incident.primary_machine_id == machine_id)
    return query.first() is not None


# ---------------------------------------------------------------------------
# Création d'un incident
# ---------------------------------------------------------------------------
def create_incident(
    db: Session,
    verdict_info: Dict[str, Any],
    machine_id: Optional[int] = None,
    diagnostic: Optional[Dict[str, Any]] = None,
    assessment: Optional[Dict[str, Any]] = None,
) -> Incident:
    """Crée un incident en base à partir d'un verdict."""
    incident = Incident(
        incident_id=_new_incident_id(),
        incident_ts=datetime.now(timezone.utc),
        verdict=verdict_info["verdict"],
        severity=verdict_info["severity"],
        confidence=verdict_info["confidence"],
        status="new",
        title=verdict_info["description"][:255],
        description=verdict_info["description"],
        primary_machine_id=machine_id,
        machine_ids_json={"ids": [machine_id]} if machine_id else None,
        event_ids_json=None,
        alert_ids_json=(
            {"wazuh_alert_id": assessment["alert_id"]}
            if assessment and assessment.get("alert_id") else None
        ),
        evidence_json=verdict_info.get("evidence"),
        recommendation=_recommendation_for(verdict_info["verdict"]),
        proposed_action=_proposed_action_for(verdict_info["verdict"], assessment),
        action_target=(assessment or {}).get("src_ip"),
    )
    db.add(incident)
    return incident


# ---------------------------------------------------------------------------
# Helpers pour recommandations et actions
# ---------------------------------------------------------------------------
def _recommendation_for(verdict: str) -> str:
    return {
        VERDICT_NORMAL: "Aucune action requise.",
        VERDICT_TECHNICAL_ANOMALY: "Vérifier la machine concernée (CPU, RAM, disque).",
        VERDICT_NETWORK_FAILURE: "Vérifier le lien réseau et la disponibilité de la machine.",
        VERDICT_SECURITY_ALERT: "Examiner l'alerte de sécurité et les journaux associés.",
        VERDICT_SUSPECTED_ATTACK: "Bloquer l'IP source après validation humaine, analyser les logs.",
        VERDICT_MIXED_INCIDENT: "Bloquer l'IP source, vérifier la machine, analyser les logs.",
        VERDICT_INVESTIGATION_REQUIRED: "Investigation manuelle requise par un analyste.",
    }.get(verdict, "Investigation requise.")


def _proposed_action_for(
    verdict: str,
    assessment: Optional[Dict[str, Any]],
) -> Optional[str]:
    if verdict in (VERDICT_SUSPECTED_ATTACK, VERDICT_MIXED_INCIDENT):
        return "block_ip"
    if verdict == VERDICT_SECURITY_ALERT:
        return "investigate"
    if verdict == VERDICT_NETWORK_FAILURE:
        return "check_link"
    if verdict == VERDICT_TECHNICAL_ANOMALY:
        return "check_machine"
    return None