#!/usr/bin/env python3
"""
NETVIGIE — Lancement isolé de l'Agent 04 (Correlation)
Usage : ./venv/bin/python scripts/run_correlation.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.correlation import AgentCorrelation
from backend.core.config import settings, netvigie_config
from backend.core.database import test_connection
from backend.core.redis_bus import get_bus


def main():
    print("=" * 60)
    print("  NETVIGIE — Agent 04 : Correlation & Response")
    print("=" * 60)
    print(f"  Intervalle           : {settings.correlation_interval_seconds}s")
    print(f"  Fenêtre de corrélation: {settings.correlation_time_window_seconds}s")
    print(f"  Seuil précédence     : {netvigie_config.correlation.get('precedence_threshold_ms')} ms")
    print(f"  PostgreSQL           : {'OK' if test_connection() else 'ERREUR'}")
    print(f"  Redis                : {'OK' if get_bus().ping() else 'ERREUR'}")
    print("=" * 60)
    print("  Ctrl+C pour arrêter")
    print()

    agent = AgentCorrelation()
    agent.start()


if __name__ == "__main__":
    main()