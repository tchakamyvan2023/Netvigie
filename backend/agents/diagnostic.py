"""
NETVIGIE — Agent 02 : Diagnostic
Consomme machine_updates depuis Redis, ping les machines,
publie des diagnostics sur Redis, met à jour la base.
"""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.agents.base_agent import BaseAgent
from backend.core.config import settings
from backend.core.database import db_session
from backend.core.redis_bus import (
    STREAM_MACHINE_UPDATES,
    STREAM_DIAGNOSTICS,
)
from backend.models.machine import Machine
from backend.services import diagnostic_service, event_service
from backend.services.diagnostic_service import (
    STATUS_ANOMALY,
    STATUS_NORMAL,
    STATUS_UNREACHABLE,
    diagnose_machine,
    is_anomaly,
    update_machine_network,
)


class AgentDiagnostic(BaseAgent):
    NAME = "diagnostic"
    DEFAULT_INTERVAL = settings.diagnostic_interval_seconds

    #: Consumer group Redis
    CONSUMER_GROUP = "diagnostic"
    CONSUMER_NAME = "diagnostic-1"

    def __init__(self, interval: int = None):
        super().__init__(interval)
        self._ensure_consumer_group()

    def _ensure_consumer_group(self) -> None:
        try:
            self.bus.ensure_group(STREAM_MACHINE_UPDATES, self.CONSUMER_GROUP)
            self.logger.info(f"Consumer group '{self.CONSUMER_GROUP}' prêt")
        except Exception as e:
            self.logger.warning(f"Création consumer group : {e}")

    # ------------------------------------------------------------------
    # Point d'entrée d'une itération
    # ------------------------------------------------------------------
    def process(self) -> Dict[str, Any]:
        stats = {"events": 0, "errors": 0, "summary": ""}

        # 1. Lire les machine_updates depuis Redis
        messages = self.bus.read_group(
            STREAM_MACHINE_UPDATES,
            self.CONSUMER_GROUP,
            self.CONSUMER_NAME,
            count=50,
            block_ms=1000,
        )

        if not messages:
            # Pas de nouveau message : on ping quand même toutes les machines actives
            self.logger.debug("Aucun machine_update, on ping les machines actives en base")
            with db_session() as db:
                machines = (
                    db.query(Machine)
                    .filter(Machine.status == "active", Machine.is_excluded == False)  # noqa: E712
                    .all()
                )
                for m in machines:
                    self._diagnose_and_publish(db, m, stats)
        else:
            with db_session() as db:
                for msg_id, payload in messages:
                    machine_id = payload.get("machine_id")
                    if not machine_id:
                        self.bus.ack(STREAM_MACHINE_UPDATES, self.CONSUMER_GROUP, msg_id)
                        continue
                    machine = db.query(Machine).filter(Machine.id == machine_id).first()
                    if not machine:
                        self.bus.ack(STREAM_MACHINE_UPDATES, self.CONSUMER_GROUP, msg_id)
                        continue
                    if machine.is_excluded:
                        self.bus.ack(STREAM_MACHINE_UPDATES, self.CONSUMER_GROUP, msg_id)
                        continue
                    self._diagnose_and_publish(db, machine, stats)
                    self.bus.ack(STREAM_MACHINE_UPDATES, self.CONSUMER_GROUP, msg_id)

        stats["summary"] = stats["summary"].strip(" |") or "ok"
        return stats

    # ------------------------------------------------------------------
    # Diagnostic d'une machine
    # ------------------------------------------------------------------
    def _diagnose_and_publish(self, db, machine: Machine, stats: Dict[str, Any]) -> None:
        try:
            diag = diagnose_machine(
                machine,
                ping_timeout_s=settings.diagnostic_ping_timeout_seconds,
            )
            update_machine_network(db, machine.id, diag)
            db.commit()

            # Publier sur Redis
            self.bus.publish(STREAM_DIAGNOSTICS, diag)
            stats["events"] += 1

            status = diag["status"]
            latency = diag.get("latency_ms")
            loss = diag.get("packet_loss_percent")
            stats["summary"] += f"{machine.hostname}:{status} | "

            # Log
            if status == STATUS_NORMAL:
                self.logger.debug(
                    f"{machine.hostname} OK (lat={latency}ms, loss={loss}%)"
                )
            elif status == STATUS_ANOMALY:
                self.logger.warning(
                    f"⚠ {machine.hostname} ANOMALY "
                    f"(lat={latency}ms, loss={loss}%)"
                )
                self._create_anomaly_event(db, machine, diag)
            elif status == STATUS_UNREACHABLE:
                self.logger.warning(f"⚠ {machine.hostname} UNREACHABLE")
                self._create_anomaly_event(db, machine, diag)

        except Exception as e:
            stats["errors"] += 1
            self.logger.error(f"Diagnostic {machine.hostname} échoué : {e}")

    def _create_anomaly_event(self, db, machine: Machine, diag: Dict[str, Any]) -> None:
        try:
            event_service.create_event(
                db,
                source="diagnostic",
                event_type="network_anomaly",
                category="network",
                severity="high" if diag["status"] == STATUS_ANOMALY else "critical",
                confidence=0.85,
                machine_id=machine.id,
                src_ip=machine.ip,
                description=(
                    f"{machine.hostname} : {diag['status']} "
                    f"(lat={diag.get('latency_ms')}ms, "
                    f"loss={diag.get('packet_loss_percent')}%)"
                ),
                evidence={
                    "status": diag["status"],
                    "latency_ms": diag.get("latency_ms"),
                    "packet_loss_percent": diag.get("packet_loss_percent"),
                    "thresholds": diag.get("thresholds"),
                },
            )
            db.commit()
        except Exception as e:
            self.logger.warning(f"Création event anomalie échouée : {e}")