#!/usr/bin/env python3
"""
NETVIGIE — Lance les 4 agents en parallèle
Utilisé par systemd (netvigie-agents.service)
Gère SIGTERM/SIGINT pour un arrêt propre.
"""
import signal
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.collector import AgentCollector
from backend.agents.diagnostic import AgentDiagnostic
from backend.agents.security import AgentSecurity
from backend.agents.correlation import AgentCorrelation
from backend.core.logging_config import setup_logging

logger = setup_logging("netvigie.agents")

_shutdown = threading.Event()


def _handle_signal(signum, frame):
    logger.info(f"Signal {signum} reçu — arrêt en cours...")
    _shutdown.set()


def _run_agent(agent, name):
    """Boucle de l'agent avec vérification périodique du shutdown."""
    try:
        agent.start()
    except Exception as e:
        logger.error(f"Agent {name} crashé : {e}")


def main():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("=== Démarrage des 4 agents NETVIGIE ===")

    agents = [
        (AgentCollector(), "collector"),
        (AgentDiagnostic(), "diagnostic"),
        (AgentSecurity(), "security"),
        (AgentCorrelation(), "correlation"),
    ]

    threads = []
    for agent, name in agents:
        t = threading.Thread(target=_run_agent, args=(agent, name), daemon=True, name=name)
        t.start()
        threads.append(t)
        logger.info(f"Agent {name} lancé (thread {t.name})")

    # Attendre le signal d'arrêt
    while not _shutdown.is_set():
        time.sleep(1)

    logger.info("=== Arrêt des agents ===")
    for agent, name in agents:
        try:
            agent.stop()
        except Exception as e:
            logger.warning(f"Arrêt {name} : {e}")

    # Attendre max 10s que les threads se terminent
    for t in threads:
        t.join(timeout=10)

    logger.info("=== Tous les agents arrêtés ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())