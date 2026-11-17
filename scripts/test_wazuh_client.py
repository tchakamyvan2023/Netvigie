#!/usr/bin/env python3
"""
NETVIGIE — Test complet du client Wazuh (Module 2)
Affiche un rapport détaillé de toutes les fonctionnalités.
Usage : ./venv/bin/python scripts/test_wazuh_client.py
"""
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import settings
from backend.integrations.wazuh_api import get_wazuh_client
from backend.integrations.wazuh_indexer import get_indexer_client
from backend.core.exceptions import WazuhError


def sep(title: str):
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def ok(msg: str):
    print(f"  ✓ {msg}")


def err(msg: str):
    print(f"  ✗ {msg}")


def main():
    results = {"ok": 0, "err": 0}

    def record(success: bool):
        if success:
            results["ok"] += 1
        else:
            results["err"] += 1

    # --------------------------------------------------------------
    sep("1. Configuration")
    # --------------------------------------------------------------
    print(f"  URL API     : {settings.wazuh_api_url}")
    print(f"  URL Indexer : {settings.wazuh_indexer_url}")
    print(f"  User API    : {settings.wazuh_api_user}")
    print(f"  User Indexer: {settings.wazuh_indexer_user}")

    # --------------------------------------------------------------
    sep("2. Authentification API")
    # --------------------------------------------------------------
    try:
        client = get_wazuh_client()
        if client.ping():
            ok("Authentification API réussie")
            record(True)
        else:
            err("Authentification API échouée")
            record(False)
            return summarize(results)
    except Exception as e:
        err(f"Exception : {e}")
        record(False)
        return summarize(results)

    # --------------------------------------------------------------
    sep("3. Info Manager")
    # --------------------------------------------------------------
    try:
        info = client.get_manager_info()
        ok(f"Manager : {info.get('version', '?')} ({info.get('type', '?')})")
        record(True)
    except Exception as e:
        err(f"Erreur : {e}")
        record(False)

    # --------------------------------------------------------------
    sep("4. Liste des agents")
    # --------------------------------------------------------------
    try:
        agents = client.list_all_agents()
        ok(f"{len(agents)} agent(s) trouvé(s)")
        for a in agents:
            status = a.get("status", "?")
            marker = "●" if status == "active" else "○"
            print(f"      {marker} ID {a.get('id')} | {a.get('name')} "
                  f"| {a.get('ip', '?')} | {status}")
        record(True)
    except Exception as e:
        err(f"Erreur : {e}")
        agents = []
        record(False)

    # --------------------------------------------------------------
    sep("5. Syscollector (sur les agents actifs)")
    # --------------------------------------------------------------
    active_agents = [a for a in agents if a.get("status") == "active"]
    if not active_agents:
        print("  ⚠ Aucun agent actif, étape ignorée")
    else:
        for agent in active_agents[:2]:  # on limite à 2 pour lisibilité
            agent_id = str(agent.get("id"))
            name = agent.get("name", "?")
            print(f"\n  --- Agent {agent_id} ({name}) ---")
            try:
                hw = client.get_syscollector_hardware(agent_id)
                if hw:
                    cpu = hw.get("cpu", {})
                    ram = hw.get("ram", {})
                    print(f"      CPU    : {cpu.get('name', '?')} "
                          f"({cpu.get('cores', '?')} cores)")
                    print(f"      RAM    : {ram.get('total', 0) // (1024)} Mo "
                          f"({ram.get('usage', '?')}% utilisé)")
                    ok(f"Hardware récupéré")
                    record(True)
                else:
                    err("Hardware vide (agent peut-être trop récent)")
                    record(False)

                os_info = client.get_syscollector_os(agent_id)
                if os_info:
                    print(f"      OS     : {os_info.get('os', {}).get('name', '?')} "
                          f"{os_info.get('os', {}).get('version', '')}")
                    ok("OS récupéré")
                    record(True)

                net = client.get_syscollector_network_addr(agent_id)
                if net:
                    print(f"      Réseau : {len(net)} adresse(s)")
                    ok("Réseau récupéré")
                    record(True)

            except Exception as e:
                err(f"Erreur syscollector : {e}")
                record(False)

    # --------------------------------------------------------------
    sep("6. Alertes récentes (API)")
    # --------------------------------------------------------------
    try:
        alerts = client.get_recent_alerts(since_seconds=3600, min_level=3)
        ok(f"{len(alerts)} alerte(s) dans la dernière heure")
        for a in alerts[:5]:
            rule = a.get("rule", {})
            print(f"      - [{a.get('timestamp', '?')[:19]}] "
                  f"L{rule.get('level', '?')} | {rule.get('description', '?')[:60]}")
        record(True)
    except Exception as e:
        err(f"Erreur alertes API : {e}")
        record(False)

    # --------------------------------------------------------------
    sep("7. Indexer")
    # --------------------------------------------------------------
    try:
        indexer = get_indexer_client()
        if indexer.ping():
            ok("Indexer accessible")
            record(True)
        else:
            err("Indexer injoignable")
            record(False)
            return summarize(results)

        count = indexer.count_alerts(min_level=3, since_minutes=60)
        ok(f"{count} alerte(s) indexée(s) dans la dernière heure")
        record(True)

        recent = indexer.get_recent_alerts(size=3, min_level=3, since_minutes=60)
        for a in recent:
            rule = a.get("rule", {})
            print(f"      - L{rule.get('level', '?')} | "
                  f"{rule.get('description', '?')[:60]}")
        record(True)
    except Exception as e:
        err(f"Erreur Indexer : {e}")
        record(False)

    return summarize(results)


def summarize(results):
    print()
    print("=" * 70)
    print("  RAPPORT FINAL")
    print("=" * 70)
    total = results["ok"] + results["err"]
    print(f"  ✓ {results['ok']} test(s) réussi(s)")
    print(f"  ✗ {results['err']} test(s) échoué(s)")
    print(f"  Total : {total}")
    print("=" * 70)
    return 0 if results["err"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())