"""
NETVIGIE — Classe de base commune aux 4 agents
Gère : cycle de vie, heartbeat, publication Redis, erreurs, métriques.
Supporte les consumer groups Redis pour les agents qui consomment des streams.
"""
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from backend.core.database import db_session
from backend.core.logging_config import setup_logging
from backend.core.redis_bus import get_bus, STREAM_AGENT_HEARTBEATS
from backend.models.agent_netvigie import AgentNetvigie


class BaseAgent(ABC):
    """Agent abstrait : chaque agent hérite et implémente `process()`."""

    #: Nom unique de l'agent (doit correspondre à `agents_netvigie.name`)
    NAME: str = "base"

    #: Intervalle par défaut (secondes), surchargé par les sous-classes
    DEFAULT_INTERVAL: int = 10

    #: Stream Redis consommé (optionnel — vide si l'agent ne consomme pas)
    CONSUMER_STREAM: str = ""

    #: Consumer group Redis (optionnel — vide si l'agent ne consomme pas)
    CONSUMER_GROUP: str = ""

    #: Nom du consumer dans le groupe (optionnel)
    CONSUMER_NAME: str = ""

    def __init__(self, interval: Optional[int] = None):
        self.logger = setup_logging(f"netvigie.agent.{self.NAME}")
        self.interval = interval or self.DEFAULT_INTERVAL
        self.bus = get_bus()

        self._running = False
        self._events_processed = 0
        self._errors_count = 0
        self._total_processing_ms = 0.0
        self._iterations = 0

        # Initialisation du consumer group si défini par la sous-classe
        if self.CONSUMER_STREAM and self.CONSUMER_GROUP:
            self._ensure_consumer_group()

    # ------------------------------------------------------------------
    # Consumer group Redis
    # ------------------------------------------------------------------
    def _ensure_consumer_group(self) -> None:
        """Crée le consumer group s'il n'existe pas déjà."""
        try:
            self.bus.ensure_group(self.CONSUMER_STREAM, self.CONSUMER_GROUP)
            self.logger.info(
                f"Consumer group '{self.CONSUMER_GROUP}' prêt "
                f"sur stream '{self.CONSUMER_STREAM}'"
            )
        except Exception as e:
            self.logger.warning(f"Création consumer group échouée : {e}")

    def read_stream(
        self,
        count: int = 50,
        block_ms: int = 1000,
    ):
        """
        Lit les nouveaux messages du stream consommé.
        Retourne une liste de tuples (msg_id, payload).
        Retourne [] si l'agent n'est pas configuré pour consommer.
        """
        if not (self.CONSUMER_STREAM and self.CONSUMER_GROUP):
            return []
        return self.bus.read_group(
            self.CONSUMER_STREAM,
            self.CONSUMER_GROUP,
            self.CONSUMER_NAME or f"{self.NAME}-1",
            count=count,
            block_ms=block_ms,
        )

    def ack(self, msg_id: str) -> None:
        """Acquitte un message consommé."""
        if not (self.CONSUMER_STREAM and self.CONSUMER_GROUP):
            return
        try:
            self.bus.ack(self.CONSUMER_STREAM, self.CONSUMER_GROUP, msg_id)
        except Exception as e:
            self.logger.warning(f"ACK {msg_id} échoué : {e}")

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Démarre l'agent (bloquant jusqu'à Ctrl+C)."""
        self._running = True
        self.logger.info(f"=== Agent {self.NAME} démarré (interval={self.interval}s) ===")
        self._update_status("running")

        try:
            while self._running:
                self._iteration()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            self.logger.info(f"=== Agent {self.NAME} interrompu ===")
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        self._update_status("stopped")
        self.logger.info(f"=== Agent {self.NAME} arrêté ===")

    # ------------------------------------------------------------------
    # Une itération = un tour de collecte + heartbeat
    # ------------------------------------------------------------------
    def _iteration(self) -> None:
        self._iterations += 1
        t_start = time.time()
        try:
            stats = self.process() or {}
            self._events_processed += stats.get("events", 0)
            self._errors_count += stats.get("errors", 0)
            elapsed_ms = (time.time() - t_start) * 1000
            self._total_processing_ms += elapsed_ms

            avg = self._total_processing_ms / self._iterations
            self.logger.info(
                f"[iter #{self._iterations}] {elapsed_ms:.0f}ms | "
                f"{stats.get('summary', 'ok')} | "
                f"total: {self._events_processed} events, {self._errors_count} errors"
            )
        except Exception as e:
            self._errors_count += 1
            self.logger.error(f"Erreur dans process() : {e}\n{traceback.format_exc()}")

        self._heartbeat()

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------
    def _heartbeat(self) -> None:
        avg = (
            self._total_processing_ms / self._iterations
            if self._iterations
            else 0.0
        )
        try:
            with db_session() as db:
                agent = (
                    db.query(AgentNetvigie)
                    .filter(AgentNetvigie.name == self.NAME)
                    .first()
                )
                if agent:
                    agent.status = "running" if self._running else "stopped"
                    agent.last_heartbeat = datetime.now(timezone.utc)
                    agent.events_processed = self._events_processed
                    agent.errors_count = self._errors_count
                    agent.avg_processing_ms = round(avg, 2)
        except Exception as e:
            self.logger.warning(f"Heartbeat DB échoué : {e}")

        # Publier sur Redis
        try:
            self.bus.publish(STREAM_AGENT_HEARTBEATS, {
                "agent": self.NAME,
                "status": "running" if self._running else "stopped",
                "events_processed": self._events_processed,
                "errors_count": self._errors_count,
                "avg_processing_ms": round(avg, 2),
                "ts": time.time(),
            })
        except Exception as e:
            self.logger.warning(f"Heartbeat Redis échoué : {e}")

    # ------------------------------------------------------------------
    # À implémenter par les sous-classes
    # ------------------------------------------------------------------
    @abstractmethod
    def process(self) -> dict:
        """
        Une itération de collecte/analyse.
        Retourne un dict {"events": int, "errors": int, "summary": str}.
        """
        raise NotImplementedError

    def _update_status(self, status: str) -> None:
        try:
            with db_session() as db:
                agent = (
                    db.query(AgentNetvigie)
                    .filter(AgentNetvigie.name == self.NAME)
                    .first()
                )
                if agent:
                    agent.status = status
                    agent.last_heartbeat = datetime.now(timezone.utc)
        except Exception as e:
            self.logger.warning(f"Update status échoué : {e}")