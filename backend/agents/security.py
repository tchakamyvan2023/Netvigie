"""
NETVIGIE — Agent 03 : Security Analyst
Analyse les alertes Wazuh, classifie, calcule le risque,
détecte les motifs, publie des security_assessments sur Redis.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.agents.base_agent import BaseAgent
from backend.core.config import settings
from backend.core.database import db_session
from backend.core.redis_bus import STREAM_SECURITY_ASSESSMENTS
from backend.models.alert import Alert
from backend.services import event_service, security_service
from backend.services.security_service import (
    CAT_SSH_BRUTE_FORCE,
    CAT_PRIVILEGE_ESCALATION,
    CAT_MALWARE,
    CAT_WEB_ATTACK,
    analyze_alert,
    get_unanalyzed_alerts,
)


# Catégories qui justifient un événement `security_incident`
CRITICAL_CATEGORIES = {
    CAT_SSH_BRUTE_FORCE,
    CAT_PRIVILEGE_ESCALATION,
    CAT_MALWARE,
    CAT_WEB_ATTACK,
}

# Seuil de score de risque pour créer un événement
RISK_SCORE_THRESHOLD = 75.0


class AgentSecurity(BaseAgent):
    NAME = "security"
    DEFAULT_INTERVAL = settings.security_interval_seconds

    def __init__(self, interval: int = None):
        super().__init__(interval)

    # ------------------------------------------------------------------
    # Point d'entrée d'une itération
    # ------------------------------------------------------------------
    def process(self) -> Dict[str, Any]:
        stats = {"events": 0, "errors": 0, "summary": ""}

        with db_session() as db:
            alerts = get_unanalyzed_alerts(db, limit=100)
            if not alerts:
                stats["summary"] = "aucune nouvelle alerte"
                return stats

            analyzed = 0
            incidents = 0
            patterns = 0

            for alert in alerts:
                try:
                    assessment = analyze_alert(db, alert)
                    self.bus.publish(STREAM_SECURITY_ASSESSMENTS, assessment)
                    stats["events"] += 1
                    analyzed += 1

                    if assessment["patterns"]:
                        patterns += 1

                    # Créer un événement si critique
                    if self._should_create_incident(assessment):
                        self._create_security_incident(db, alert, assessment)
                        incidents += 1

                except Exception as e:
                    stats["errors"] += 1
                    self.logger.error(f"Analyse alerte {alert.wazuh_alert_id} échouée : {e}")

            db.commit()

            stats["summary"] = (
                f"analysées:{analyzed} "
                f"motifs:{patterns} "
                f"incidents:{incidents}"
            )
            if incidents:
                self.logger.warning(
                    f"⚠ {incidents} incident(s) critique(s) détecté(s)"
                )

        return stats

    # ------------------------------------------------------------------
    # Décision de créer un incident
    # ------------------------------------------------------------------
    def _should_create_incident(self, assessment: Dict[str, Any]) -> bool:
        if assessment["risk_score"] >= RISK_SCORE_THRESHOLD:
            return True
        if assessment["category"] in CRITICAL_CATEGORIES:
            return True
        if assessment.get("is_brute_force") or assessment.get("is_port_scan"):
            return True
        return False

    # ------------------------------------------------------------------
    # Création d'un événement security_incident
    # ------------------------------------------------------------------
    def _create_security_incident(
        self,
        db,
        alert: Alert,
        assessment: Dict[str, Any],
    ) -> None:
        try:
            severity = "critical" if assessment["risk_score"] >= 90 else "high"
            description = (
                f"[{assessment['category']}] {assessment['rule_description']} "
                f"(risque {assessment['risk_score']}/100"
            )
            if assessment["patterns"]:
                description += f", motifs: {', '.join(assessment['patterns'])}"
            description += ")"

            event_service.create_event(
                db,
                source="security",
                event_type="security_incident",
                category=assessment["category"],
                severity=severity,
                confidence=min(assessment["risk_score"] / 100.0, 1.0),
                machine_id=None,
                src_ip=assessment.get("src_ip"),
                dst_ip=assessment.get("dst_ip"),
                user=assessment.get("user"),
                description=description,
                evidence={
                    "alert_id": assessment["alert_id"],
                    "risk_score": assessment["risk_score"],
                    "patterns": assessment["patterns"],
                    "mitre_ids": assessment.get("mitre_ids"),
                    "rule_level": assessment["rule_level"],
                },
            )
            db.commit()
            self.logger.warning(f"🔴 Incident créé : {description[:100]}")
        except Exception as e:
            self.logger.warning(f"Création incident échouée : {e}")