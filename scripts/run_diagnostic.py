#!/usr/bin/env python3
"""
NETVIGIE — Lancement isolé de l'Agent 02 (Diagnostic)
Usage : ./venv/bin/python scripts/run_diagnostic.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.diagnostic import AgentDiagnostic
from backend.core.config import settings, netvigie_config
from backend.core.database import test_connection
from backend.core.redis_bus import get_bus


def main():
    print("=" * 60)
    print("  NETVIGIE — Agent 02 : Diagnostic")
    print("=" * 60)
    print(f"  Intervalle     : {settings.diagnostic_interval_seconds}s")
    print(f"  Ping timeout   : {settings.diagnostic_ping_timeout_seconds}s")
    print(f"  Seuil latence  : {netvigie_config.thresholds.get('latency_ms')} ms")
    print(f"  Seuil pertes   : {netvigie_config.thresholds.get('packet_loss_percent')} %")
    print(f"  PostgreSQL     : {'OK' if test_connection() else 'ERREUR'}")
    print(f"  Redis          : {'OK' if get_bus().ping() else 'ERREUR'}")
    print("=" * 60)
    print("  Ctrl+C pour arrêter")
    print()

    agent = AgentDiagnostic()
    agent.start()


if __name__ == "__main__":
    main()