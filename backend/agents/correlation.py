"""
NETVIGIE — Agent 04 : Correlation & Response
Centre décisionnel : croise diagnostics (Agent 02) et
assessments (Agent 03), produit un verdict, crée un incident.

Corrections :
- Utilisation de incident_exists_recent() pour éviter les doublons
- Fenêtre de déduplication de 5 minutes
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, and_

from backend.agents.base_agent import BaseAgent
from backend.core.config import settings
from backend.core.database import db_session
from backend.core.redis_bus import STREAM_INCIDENTS
from backend.models.alert import Alert
from backend.models.event import Event
from backend.models.machine import Machine
from backend.services import correlation_service, event_service
from backend.services.correlation_service import (
    VERDICT_NORMAL,
    create_incident,
    decide_verdict,
    incident_exists_recent,   # ← NOUVEAU : déduplication
)


class AgentCorrelation(BaseAgent):
    NAME = "correlation"
    DEFAULT_INTERVAL = settings.correlation_interval_seconds

    #: Fenêtre pour considérer un diagnostic/assessment "récent"
    RECENT_WINDOW_SECONDS = 120

    #: Fenêtre de déduplication (minutes)
    DEDUP_WINDOW_MINUTES = 5

    def __init__(self, interval: int = None):
        super().__init__(interval)
        self._processed_signatures: set = set()

    # ------------------------------------------------------------------
    # Point d'entrée d'une itération
    # ------------------------------------------------------------------
    def process(self) -> Dict[str, Any]:
        stats = {"events": 0, "errors": 0, "summary": ""}

        with db_session() as db:
            machines = (
                db.query(Machine)
                .filter(Machine.status == "active", Machine.is_excluded == False)  # noqa: E712
                .all()
            )

            verdicts_count: Dict[str, int] = defaultdict(int)
            incidents_created = 0
            incidents_skipped = 0

            for machine in machines:
                try:
                    diagnostic = self._get_latest_diagnostic(machine)
                    assessment = self._get_latest_assessment(db, machine)

                    # Skip si rien de récent
                    if not diagnostic and not assessment:
                        continue

                    verdict_info = decide_verdict(diagnostic, assessment)
                    verdicts_count[verdict_info["verdict"]] += 1

                    # Ne créer un incident que si verdict != NORMAL
                    if verdict_info["verdict"] == VERDICT_NORMAL:
                        continue

                    # ------------------------------------------------------
                    # DÉDUPLICATION EN BASE (persistante)
                    # ------------------------------------------------------
                    if incident_exists_recent(
                        db,
                        machine_id=machine.id,
                        verdict=verdict_info["verdict"],
                        window_minutes=self.DEDUP_WINDOW_MINUTES,
                    ):
                        incidents_skipped += 1
                        self.logger.debug(
                            f"Incident {verdict_info['verdict']} déjà existant "
                            f"pour {machine.hostname} (ignoré)"
                        )
                        continue

                    # ------------------------------------------------------
                    # DÉDUPLICATION EN MÉMOIRE (cache court terme)
                    # ------------------------------------------------------
                    signature = (
                        machine.id,
                        verdict_info["verdict"],
                        (assessment or {}).get("alert_id") or "",
                        (diagnostic or {}).get("diagnosed_at") or "",
                    )
                    if signature in self._processed_signatures:
                        incidents_skipped += 1
                        continue
                    self._processed_signatures.add(signature)

                    # ------------------------------------------------------
                    # CRÉATION DE L'INCIDENT
                    # ------------------------------------------------------
                    incident = create_incident(
                        db,
                        verdict_info,
                        machine_id=machine.id,
                        diagnostic=diagnostic,
                        assessment=assessment,
                    )
                    db.commit()
                    incidents_created += 1
                    stats["events"] += 1

                    # Publier sur Redis
                    self.bus.publish(STREAM_INCIDENTS, {
                        "incident_id": incident.incident_id,
                        "verdict": incident.verdict,
                        "severity": incident.severity,
                        "confidence": incident.confidence,
                        "machine_id": machine.id,
                        "hostname": machine.hostname,
                        "ip": machine.ip,
                        "description": incident.description,
                        "proposed_action": incident.proposed_action,
                        "action_target": incident.action_target,
                        "ts": incident.incident_ts.timestamp(),
                    })

                    # Créer un événement de traçabilité
                    event_service.create_event(
                        db,
                        source="correlation",
                        event_type="incident_created",
                        category=verdict_info["verdict"],
                        severity=verdict_info["severity"],
                        confidence=verdict_info["confidence"],
                        machine_id=machine.id,
                        src_ip=machine.ip,
                        description=verdict_info["description"],
                        evidence=verdict_info.get("evidence"),
                    )
                    db.commit()

                    self.logger.warning(
                        f"🔴 Incident {incident.incident_id} "
                        f"[{incident.verdict}] {machine.hostname}"
                    )

                except Exception as e:
                    stats["errors"] += 1
                    self.logger.error(f"Corrélation {machine.hostname} échouée : {e}")

            # Limiter la taille du cache mémoire
            if len(self._processed_signatures) > 1000:
                self._processed_signatures = set(
                    list(self._processed_signatures)[-500:]
                )

            summary = ", ".join(f"{k}:{v}" for k, v in verdicts_count.items())
            stats["summary"] = (
                f"incidents:{incidents_created} skipped:{incidents_skipped} | {summary}"
                if summary
                else f"incidents:{incidents_created} skipped:{incidents_skipped}"
            )

        return stats

    # ------------------------------------------------------------------
    # Récupération du dernier diagnostic
    # ------------------------------------------------------------------
    def _get_latest_diagnostic(self, machine: Machine) -> Optional[Dict[str, Any]]:
        """Reconstruit un diagnostic à partir des colonnes réseau de la machine."""
        if machine.last_ping_at is None:
            return None
        age = (datetime.now(timezone.utc) - machine.last_ping_at).total_seconds()
        if age > self.RECENT_WINDOW_SECONDS:
            return None

        # Reconstruire le statut
        from backend.core.config import netvigie_config
        thresholds = netvigie_config.thresholds
        latency = machine.latency_ms
        loss = machine.packet_loss_percent
        status = "NORMAL"
        if latency is None and loss is None:
            return None
        if latency is None:
            status = "UNREACHABLE"
        else:
            if latency > float(thresholds.get("latency_ms", 300)):
                status = "ANOMALY"
            if loss is not None and loss > float(thresholds.get("packet_loss_percent", 3.0)):
                status = "ANOMALY"

        return {
            "machine_id": machine.id,
            "hostname": machine.hostname,
            "ip": machine.ip,
            "status": status,
            "latency_ms": latency,
            "packet_loss_percent": loss,
            "ts": machine.last_ping_at.timestamp(),
            "diagnosed_at": machine.last_ping_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Récupération du dernier assessment
    # ------------------------------------------------------------------
    def _get_latest_assessment(self, db, machine: Machine) -> Optional[Dict[str, Any]]:
        """Récupère la dernière alerte analysée pour cette machine."""
        if not machine.agent_id:
            return None

        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=self.RECENT_WINDOW_SECONDS
        )
        alert = (
            db.query(Alert)
            .filter(
                and_(
                    Alert.agent_id == machine.agent_id,
                    Alert.analyzed_at.isnot(None),
                    Alert.alert_ts >= cutoff,
                )
            )
            .order_by(desc(Alert.alert_ts))
            .first()
        )
        if not alert:
            return None

        return {
            "alert_id": alert.wazuh_alert_id,
            "agent_id": alert.agent_id,
            "agent_name": alert.agent_name,
            "rule_id": alert.rule_id,
            "rule_level": alert.rule_level,
            "rule_description": alert.rule_description,
            "category": alert.security_category,
            "severity": alert.severity,
            "risk_score": alert.risk_score,
            "src_ip": alert.src_ip,
            "dst_ip": alert.dst_ip,
            "user": alert.user,
            "mitre_ids": alert.mitre_ids,
            "patterns": [],
            "is_brute_force": alert.security_category == "SSH_BRUTE_FORCE",
            "is_port_scan": alert.security_category == "PORT_SCAN",
            "alert_ts": alert.alert_ts.timestamp() if alert.alert_ts else 0,
            "analyzed_at": alert.analyzed_at.isoformat() if alert.analyzed_at else None,
        }