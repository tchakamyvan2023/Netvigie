#!/usr/bin/env python3
"""
NETVIGIE — Lancement isolé de l'Agent 03 (Security Analyst)
Usage : ./venv/bin/python scripts/run_security.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.security import AgentSecurity, RISK_SCORE_THRESHOLD
from backend.core.config import settings, netvigie_config
from backend.core.database import test_connection
from backend.core.redis_bus import get_bus


def main():
    print("=" * 60)
    print("  NETVIGIE — Agent 03 : Security Analyst")
    print("=" * 60)
    print(f"  Intervalle          : {settings.security_interval_seconds}s")
    print(f"  Seuil incident      : risk_score >= {RISK_SCORE_THRESHOLD}")
    print(f"  Seuil SSH brute     : {netvigie_config.thresholds.get('ssh_failures_10s')} / 10s")
    print(f"  PostgreSQL          : {'OK' if test_connection() else 'ERREUR'}")
    print(f"  Redis               : {'OK' if get_bus().ping() else 'ERREUR'}")
    print("=" * 60)
    print("  Ctrl+C pour arrêter")
    print()

    agent = AgentSecurity()
    agent.start()


if __name__ == "__main__":
    main()