"""
NETVIGIE — Agent 01 : Collector
Interroge Wazuh (API + Indexer), stocke en base, publie sur Redis.
"""
from typing import Any, Dict, List

from backend.agents.base_agent import BaseAgent
from backend.core.config import settings, netvigie_config
from backend.core.database import db_session
from backend.core.redis_bus import (
    STREAM_MACHINE_UPDATES,
    STREAM_SECURITY_ASSESSMENTS,
)
from backend.integrations.wazuh_api import get_wazuh_client
from backend.integrations.wazuh_indexer import get_indexer_client
from backend.models.agent_wazuh import AgentWazuh
from backend.services import alert_service, event_service, machine_service
from backend.models.machine import Machine


class AgentCollector(BaseAgent):
    NAME = "collector"
    DEFAULT_INTERVAL = settings.collector_interval_seconds

    def __init__(self, interval: int = None):
        super().__init__(interval)
        self.wazuh = get_wazuh_client()
        self.indexer = get_indexer_client()
        self._excluded_agent_ids: List[str] = []
        self._excluded_ips: List[str] = []

    # ------------------------------------------------------------------
    # Point d'entrée d'une itération
    # ------------------------------------------------------------------
    def process(self) -> Dict[str, Any]:
        stats = {"events": 0, "errors": 0, "summary": ""}

        with db_session() as db:
            # 1. Sync agents Wazuh
            try:
                agents = self.wazuh.list_all_agents()
                self._sync_agents(db, agents)
            except Exception as e:
                self.logger.error(f"Sync agents échoué : {e}")
                stats["errors"] += 1
                agents = []

            # 2. Sync machines (syscollector)
            try:
                sync_result = machine_service.sync_machines(
                    db, agents, self.wazuh.get_full_syscollector
                )
                self._excluded_agent_ids = [
                    m.agent_id for m in
                    db.query(Machine).filter(Machine.is_excluded == True).all()  # noqa: E712
                ]
                self._excluded_ips = [
                    m.ip for m in
                    db.query(Machine).filter(Machine.is_excluded == True).all()  # noqa: E712
                ]
                stats["summary"] += (
                    f"machines: +{sync_result['created']} "
                    f"~{sync_result['updated']} "
                    f"excl:{sync_result['excluded']} | "
                )

                # 3. Publier MachineUpdate sur Redis
                for m in sync_result["machines"]:
                    self._publish_machine_update(m)
                    stats["events"] += 1

                # 4. Créer un Event "machine_metric" pour chaque machine
                for m in sync_result["machines"]:
                    evt_data = event_service.event_from_machine(m)
                    event_service.create_event(db, **evt_data)
                    stats["events"] += 1

                db.commit()
            except Exception as e:
                self.logger.error(f"Sync machines échouée : {e}")
                stats["errors"] += 1

            # 5. Sync alertes (via Indexer uniquement, /alerts 404)
            try:
                raw_alerts = self.indexer.get_recent_alerts(
                    size=200,
                    min_level=3,
                    since_minutes=60,
                )
                # Ignorer les alertes du manager Wazuh lui-même (agent 000)
                raw_alerts = [
                    a for a in raw_alerts
                    if str(a.get("agent", {}).get("id", "")) != "000"
                ]

                alert_result = alert_service.sync_alerts(
                    db, raw_alerts, excluded_agent_ids=self._excluded_agent_ids
                )
                stats["summary"] += (
                    f"alerts: +{alert_result['created']} "
                    f"skip:{alert_result['skipped']} "
                    f"excl:{alert_result['excluded']} | "
                )

                # 6. Transformer les nouvelles alertes en Events + publier
                for alert in alert_result["alerts"]:
                    # Trouver la machine correspondante
                    machine = (
                        db.query(Machine)
                        .filter(Machine.agent_id == alert.agent_id)
                        .first()
                    )
                    evt_data = event_service.event_from_alert(
                        alert, machine_id=machine.id if machine else None
                    )
                    event_service.create_event(db, **evt_data)
                    stats["events"] += 1

                    self.bus.publish(STREAM_SECURITY_ASSESSMENTS, {
                        "alert_id": alert.wazuh_alert_id,
                        "agent_id": alert.agent_id,
                        "rule_level": alert.rule_level,
                        "severity": alert.severity,
                        "src_ip": alert.src_ip,
                        "dst_ip": alert.dst_ip,
                        "user": alert.user,
                        "description": alert.rule_description,
                        "ts": alert.alert_ts.timestamp()
                              if alert.alert_ts else 0,
                    })
                    stats["events"] += 1

                db.commit()
            except Exception as e:
                self.logger.error(f"Sync alertes échouée : {e}")
                stats["errors"] += 1

        stats["summary"] = stats["summary"].strip(" |") or "ok"
        return stats

    # ------------------------------------------------------------------
    # Sync agents Wazuh
    # ------------------------------------------------------------------
    def _sync_agents(self, db, agents: List[Dict[str, Any]]) -> None:
        for a in agents:
            wazuh_id = str(a.get("id", ""))
            if not wazuh_id:
                continue
            existing = (
                db.query(AgentWazuh)
                .filter(AgentWazuh.wazuh_id == wazuh_id)
                .first()
            )
            data = {
                "wazuh_id": wazuh_id,
                "name": a.get("name", "?"),
                "ip": a.get("ip", "any"),
                "status": a.get("status", "unknown"),
                "version": a.get("version"),
                "os_name": (a.get("os", {}) or {}).get("name"),
            }
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                db.add(AgentWazuh(**data))
        db.commit()

    # ------------------------------------------------------------------
    # Publication Redis
    # ------------------------------------------------------------------
    def _publish_machine_update(self, m: Machine) -> None:
        try:
            self.bus.publish(STREAM_MACHINE_UPDATES, {
                "machine_id": m.id,
                "agent_id": m.agent_id,
                "hostname": m.hostname,
                "ip": m.ip,
                "status": m.status,
                "cpu_cores": m.cpu_cores,
                "ram_total_mb": m.ram_total_mb,
                "ram_usage_percent": m.ram_usage_percent,
                "os_name": m.os_name,
                "is_excluded": m.is_excluded,
                "criticality": m.criticality,
                "ts": m.last_sync.timestamp() if m.last_sync else 0,
            })
        except Exception as e:
            self.logger.warning(f"Publish machine {m.hostname} échoué : {e}")