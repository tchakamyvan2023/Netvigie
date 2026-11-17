#!/usr/bin/env python3
"""
NETVIGIE — Lancement isolé de l'Agent 01 (Collector)
Usage : ./venv/bin/python scripts/run_collector.py
Ctrl+C pour arrêter.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.agents.collector import AgentCollector
from backend.core.config import settings
from backend.core.database import test_connection
from backend.core.redis_bus import get_bus


def main():
    print("=" * 60)
    print("  NETVIGIE — Agent 01 : Collector")
    print("=" * 60)
    print(f"  Wazuh API     : {settings.wazuh_api_url}")
    print(f"  Wazuh Indexer : {settings.wazuh_indexer_url}")
    print(f"  Intervalle    : {settings.collector_interval_seconds}s")
    print(f"  PostgreSQL    : {'OK' if test_connection() else 'ERREUR'}")
    print(f"  Redis         : {'OK' if get_bus().ping() else 'ERREUR'}")
    print("=" * 60)
    print("  Ctrl+C pour arrêter")
    print()

    agent = AgentCollector()
    agent.start()


if __name__ == "__main__":
    main()