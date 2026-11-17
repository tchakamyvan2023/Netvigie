"""
NETVIGIE — Service Alertes
Normalise et stocke les alertes Wazuh (issues de l'Indexer).

Corrections Module 6+ :
- Savepoint par alerte (isolation des erreurs SQL)
- Troncature des champs (wazuh_alert_id, description, full_log)
- Parsing des timestamps Wazuh au format +0000
- Priorité à _id (OpenSearch) sur rule.id
"""
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.core.logging_config import setup_logging
from backend.models.alert import Alert

logger = setup_logging("netvigie.service.alert")


# ---------------------------------------------------------------------------
# Mapping niveau Wazuh -> sévérité NETVIGIE
# ---------------------------------------------------------------------------
LEVEL_TO_SEVERITY = {
    range(0, 4): "info",
    range(4, 7): "low",
    range(7, 10): "medium",
    range(10, 13): "high",
    range(13, 16): "critical",
}


def _severity_from_level(level: int) -> str:
    """Convertit un niveau Wazuh (0-16) en sévérité NETVIGIE."""
    for rng, sev in LEVEL_TO_SEVERITY.items():
        if level in rng:
            return sev
    return "critical" if level >= 16 else "info"


# ---------------------------------------------------------------------------
# Parsing des timestamps Wazuh
# ---------------------------------------------------------------------------
def _parse_wazuh_ts(ts_str: Optional[str]) -> datetime:
    """
    Parse les timestamps Wazuh.
    Formats supportés :
    - '2026-11-13T16:44:15.040+0000'  (format Wazuh standard)
    - '2026-11-13T16:44:15.040Z'      (ISO avec Z)
    - '2026-11-13T16:44:15.040+00:00' (ISO avec timezone)
    """
    if not ts_str:
        return datetime.now(timezone.utc)
    try:
        # Format Wazuh : +0000 (sans deux-points)
        m = re.match(
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)\+(\d{2})(\d{2})",
            ts_str,
        )
        if m:
            base, hh, mm = m.groups()
            return datetime.fromisoformat(f"{base}+{hh}:{mm}")
        # Format ISO standard
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except Exception as e:
        logger.debug(f"Timestamp non parsable '{ts_str}': {e}")
        return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Normalisation d'une alerte brute
# ---------------------------------------------------------------------------
def _normalize_alert(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Transforme une alerte Wazuh Indexer en dict pour la table alerts.
    Tronque les champs à risque pour éviter les erreurs SQL.
    """
    try:
        # Priorité à _id (fourni par l'Indexer via hits[]._id)
        alert_id = (
            raw.get("_id")
            or raw.get("id")
            or raw.get("rule", {}).get("id")
        )
        if not alert_id:
            return None

        rule = raw.get("rule", {}) or {}
        agent = raw.get("agent", {}) or {}
        data = raw.get("data", {}) or {}
        mitre = rule.get("mitre", {}) or {}

        level = int(rule.get("level", 0))

        # Timestamp correctement parsé
        ts_str = raw.get("timestamp") or raw.get("@timestamp")
        alert_ts = _parse_wazuh_ts(ts_str)

        mitre_ids = ",".join(mitre.get("id", [])) if mitre.get("id") else None
        rule_groups = ",".join(rule.get("groups", [])) if rule.get("groups") else None

        # Troncature systématique pour éviter les dépassements
        return {
            "wazuh_alert_id": str(alert_id)[:64],
            "alert_ts": alert_ts,
            "rule_id": str(rule.get("id", ""))[:32] if rule.get("id") else None,
            "rule_level": level,
            "rule_description": (rule.get("description") or "")[:1000] or None,
            "rule_groups": (rule_groups or "")[:255] or None,
            "agent_id": str(agent.get("id", ""))[:16] if agent.get("id") else None,
            "agent_name": (agent.get("name") or "")[:128] or None,
            "src_ip": (data.get("srcip") or data.get("src_ip") or "")[:64] or None,
            "dst_ip": (data.get("dstip") or data.get("dst_ip") or "")[:64] or None,
            "user": (data.get("dstuser") or data.get("srcuser") or "")[:128] or None,
            "mitre_ids": (mitre_ids or "")[:255] or None,
            "severity": _severity_from_level(level),
            "full_log": (raw.get("full_log") or "")[:5000] or None,
            "raw_json": json.dumps(raw, default=str)[:60000],
        }
    except Exception as e:
        logger.warning(f"Normalisation alerte échouée : {str(e)[:200]}")
        return None


# ---------------------------------------------------------------------------
# Upsert (déprécié : utiliser sync_alerts)
# ---------------------------------------------------------------------------
def upsert_alert(db: Session, data: Dict[str, Any]) -> Optional[Alert]:
    """Crée une alerte si absente, retourne l'existante sinon."""
    existing = (
        db.query(Alert)
        .filter(Alert.wazuh_alert_id == data["wazuh_alert_id"])
        .first()
    )
    if existing:
        return existing
    alert = Alert(**data)
    db.add(alert)
    return alert


# ---------------------------------------------------------------------------
# Synchronisation avec SAVEPOINT par alerte
# ---------------------------------------------------------------------------
def sync_alerts(
    db: Session,
    raw_alerts: List[Dict[str, Any]],
    excluded_agent_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Synchronise les alertes depuis l'Indexer.

    Chaque alerte est traitée dans un SAVEPOINT indépendant :
    si une alerte échoue (champ trop long, contrainte violée, etc.),
    les autres continuent sans casser la transaction PostgreSQL.

    Retourne :
    {
        "created": int,
        "skipped": int,
        "excluded": int,
        "errors": int,
        "alerts": List[Alert],
    }
    """
    excluded = set(excluded_agent_ids or [])
    created = 0
    skipped = 0
    excluded_count = 0
    errors = 0
    created_alerts: List[Alert] = []

    for raw in raw_alerts:
        # SAVEPOINT : isole cette alerte du reste de la transaction
        savepoint = db.begin_nested()
        try:
            data = _normalize_alert(raw)
            if not data:
                savepoint.rollback()
                errors += 1
                continue

            if data.get("agent_id") in excluded:
                savepoint.rollback()
                excluded_count += 1
                continue

            existing = (
                db.query(Alert)
                .filter(Alert.wazuh_alert_id == data["wazuh_alert_id"])
                .first()
            )
            if existing:
                savepoint.rollback()
                skipped += 1
                continue

            alert = Alert(**data)
            db.add(alert)
            savepoint.commit()  # valide UNIQUEMENT cette alerte
            created += 1
            created_alerts.append(alert)

        except Exception as e:
            # Annule UNIQUEMENT cette alerte, pas toute la transaction
            savepoint.rollback()
            errors += 1
            logger.warning(
                f"Sync alerte échouée "
                f"(id={raw.get('_id', '?')[:30]}): {str(e)[:200]}"
            )

    # Commit final de la transaction englobante
    db.commit()

    return {
        "created": created,
        "skipped": skipped,
        "excluded": excluded_count,
        "errors": errors,
        "alerts": created_alerts,
    }


# ---------------------------------------------------------------------------
# Helpers pour récupérer les alertes
# ---------------------------------------------------------------------------
def get_recent_alerts(
    db: Session,
    since_minutes: int = 60,
    min_level: int = 0,
    limit: int = 500,
) -> List[Alert]:
    """Récupère les alertes récentes depuis la base."""
    from datetime import timedelta
    from sqlalchemy import desc

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
    return (
        db.query(Alert)
        .filter(Alert.alert_ts >= cutoff, Alert.rule_level >= min_level)
        .order_by(desc(Alert.alert_ts))
        .limit(limit)
        .all()
    )


def get_unanalyzed_alerts(db: Session, limit: int = 100) -> List[Alert]:
    """Récupère les alertes non encore analysées par l'Agent Security."""
    return (
        db.query(Alert)
        .filter(Alert.analyzed_at.is_(None))
        .order_by(Alert.alert_ts.asc())
        .limit(limit)
        .all()
    )