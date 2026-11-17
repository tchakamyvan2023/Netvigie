"""
NETVIGIE — Service Sécurité
Classifie les alertes Wazuh, calcule un score de risque,
détecte les motifs (répétition, séquence).
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from backend.core.config import netvigie_config
from backend.core.logging_config import setup_logging
from backend.models.alert import Alert

logger = setup_logging("netvigie.service.security")


# Catégories de sécurité
CAT_SSH_BRUTE_FORCE = "SSH_BRUTE_FORCE"
CAT_SSH_AUTH_FAILURE = "SSH_AUTH_FAILURE"
CAT_PORT_SCAN = "PORT_SCAN"
CAT_PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
CAT_SUSPICIOUS_COMMAND = "SUSPICIOUS_COMMAND"
CAT_MALWARE = "MALWARE"
CAT_FILE_INTEGRITY = "FILE_INTEGRITY"
CAT_WEB_ATTACK = "WEB_ATTACK"
CAT_PAM = "PAM"
CAT_OTHER = "OTHER"


# Mapping règles Wazuh → catégorie (par mots-clés dans la description)
CATEGORY_PATTERNS = [
    (CAT_SSH_BRUTE_FORCE, [
        r"brute.?force", r"multiple.*fail", r"repeated.*auth",
        r"too many authentication",
    ]),
    (CAT_SSH_AUTH_FAILURE, [
        r"authentication fail", r"failed password", r"invalid user",
        r"auth.*fail", r"sshd.*fail",
    ]),
    (CAT_PORT_SCAN, [
        r"port.?scan", r"scan detected", r"nmap",
        r"multiple.*port", r"reconnaissance",
    ]),
    (CAT_PRIVILEGE_ESCALATION, [
        r"privilege escalation", r"sudo.*root", r"su.*root",
        r"root.*session", r"elevation",
    ]),
    (CAT_SUSPICIOUS_COMMAND, [
        r"suspicious command", r"unusual command", r"malicious",
    ]),
    (CAT_MALWARE, [
        r"malware", r"virus", r"trojan", r"rootkit",
    ]),
    (CAT_FILE_INTEGRITY, [
        r"integrity", r"file.*modif", r"checksum",
    ]),
    (CAT_WEB_ATTACK, [
        r"web attack", r"sql injection", r"xss", r"directory traversal",
    ]),
    (CAT_PAM, [
        r"pam", r"session opened", r"session closed",
    ]),
]


# Groupes MITRE → sévérité de base
MITRE_WEIGHTS = {
    "T1110": 90,   # Brute Force
    "T1046": 70,   # Network Service Scanning
    "T1548": 95,   # Abuse Elevation Control
    "T1059": 80,   # Command and Scripting Interpreter
    "T1078": 85,   # Valid Accounts
    "T1190": 95,   # Exploit Public-Facing Application
}


def classify_alert(alert: Alert) -> str:
    """Classifie une alerte Wazuh en catégorie de sécurité."""
    text = " ".join(filter(None, [
        alert.rule_description or "",
        alert.rule_groups or "",
        alert.full_log or "",
    ])).lower()

    for category, patterns in CATEGORY_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return category

    return CAT_OTHER


def compute_risk_score(alert: Alert, category: str) -> float:
    """
    Calcule un score de risque 0-100 :
    - 50% : niveau de la règle Wazuh (rule_level / 15 × 100)
    - 30% : catégorie (poids par catégorie)
    - 20% : MITRE (si présent)
    """
    # Composante 1 : niveau de la règle (0-100)
    level_score = min(alert.rule_level / 15.0 * 100, 100.0)

    # Composante 2 : catégorie
    category_weights = {
        CAT_SSH_BRUTE_FORCE: 85,
        CAT_PORT_SCAN: 65,
        CAT_PRIVILEGE_ESCALATION: 90,
        CAT_MALWARE: 95,
        CAT_WEB_ATTACK: 90,
        CAT_SUSPICIOUS_COMMAND: 75,
        CAT_SSH_AUTH_FAILURE: 50,
        CAT_FILE_INTEGRITY: 70,
        CAT_PAM: 20,
        CAT_OTHER: 30,
    }
    category_score = category_weights.get(category, 30)

    # Composante 3 : MITRE
    mitre_score = 0.0
    if alert.mitre_ids:
        ids = [m.strip() for m in alert.mitre_ids.split(",")]
        mitre_score = max(
            (MITRE_WEIGHTS.get(i, 0) for i in ids), default=0.0
        )

    risk = (level_score * 0.5) + (category_score * 0.3) + (mitre_score * 0.2)
    return round(min(risk, 100.0), 2)


def detect_ssh_brute_force(
    db: Session,
    alert: Alert,
    window_seconds: int = 10,
    threshold: int = 5,
) -> bool:
    """
    Détecte une force brute SSH :
    >= `threshold` échecs d'auth depuis la même IP en `window_seconds`.
    """
    if not alert.src_ip:
        return False
    since = alert.alert_ts - timedelta(seconds=window_seconds)
    count = (
        db.query(func.count(Alert.id))
        .filter(
            and_(
                Alert.src_ip == alert.src_ip,
                Alert.alert_ts >= since,
                Alert.alert_ts <= alert.alert_ts,
                Alert.security_category.in_([
                    CAT_SSH_AUTH_FAILURE,
                    CAT_SSH_BRUTE_FORCE,
                ]),
            )
        )
        .scalar()
    )
    return (count or 0) >= threshold


def detect_port_scan(
    db: Session,
    alert: Alert,
    window_seconds: int = 30,
    threshold: int = 10,
) -> bool:
    """
    Détecte un scan de ports :
    >= `threshold` alertes de type scan depuis la même IP en `window_seconds`.
    """
    if not alert.src_ip:
        return False
    since = alert.alert_ts - timedelta(seconds=window_seconds)
    count = (
        db.query(func.count(Alert.id))
        .filter(
            and_(
                Alert.src_ip == alert.src_ip,
                Alert.alert_ts >= since,
                Alert.alert_ts <= alert.alert_ts,
                Alert.security_category == CAT_PORT_SCAN,
            )
        )
        .scalar()
    )
    return (count or 0) >= threshold


def detect_patterns(db: Session, alert: Alert, category: str) -> Dict[str, Any]:
    """
    Détecte les motifs autour d'une alerte.
    Retourne {"patterns": [...], "is_brute_force": bool, "is_port_scan": bool}
    """
    thresholds = netvigie_config.thresholds
    ssh_threshold = int(thresholds.get("ssh_failures_10s", 5))

    patterns: List[str] = []
    is_brute = False
    is_scan = False

    if category in (CAT_SSH_AUTH_FAILURE, CAT_SSH_BRUTE_FORCE):
        if detect_ssh_brute_force(db, alert, threshold=ssh_threshold):
            is_brute = True
            patterns.append(f"SSH_BRUTE_FORCE ({ssh_threshold}+ échecs en 10s)")

    if category == CAT_PORT_SCAN:
        if detect_port_scan(db, alert):
            is_scan = True
            patterns.append("PORT_SCAN (10+ ports en 30s)")

    return {
        "patterns": patterns,
        "is_brute_force": is_brute,
        "is_port_scan": is_scan,
    }


def analyze_alert(db: Session, alert: Alert) -> Dict[str, Any]:
    """
    Analyse complète d'une alerte :
    classification + score + motifs.
    """
    category = classify_alert(alert)
    risk = compute_risk_score(alert, category)
    pattern_info = detect_patterns(db, alert, category)

    # Mettre à jour l'alerte
    alert.security_category = category
    alert.risk_score = risk
    alert.pattern_detected = bool(pattern_info["patterns"])
    alert.analyzed_at = datetime.now(timezone.utc)

    # Construire l'évaluation
    assessment = {
        "alert_id": alert.wazuh_alert_id,
        "agent_id": alert.agent_id,
        "agent_name": alert.agent_name,
        "rule_id": alert.rule_id,
        "rule_level": alert.rule_level,
        "rule_description": alert.rule_description,
        "category": category,
        "severity": alert.severity,
        "risk_score": risk,
        "src_ip": alert.src_ip,
        "dst_ip": alert.dst_ip,
        "user": alert.user,
        "mitre_ids": alert.mitre_ids,
        "patterns": pattern_info["patterns"],
        "is_brute_force": pattern_info["is_brute_force"],
        "is_port_scan": pattern_info["is_port_scan"],
        "alert_ts": alert.alert_ts.timestamp() if alert.alert_ts else 0,
        "analyzed_at": alert.analyzed_at.isoformat(),
    }

    return assessment


def get_unanalyzed_alerts(db: Session, limit: int = 100) -> List[Alert]:
    """Récupère les alertes non encore analysées."""
    return (
        db.query(Alert)
        .filter(Alert.analyzed_at.is_(None))
        .order_by(Alert.alert_ts.asc())
        .limit(limit)
        .all()
    )