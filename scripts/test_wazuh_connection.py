#!/usr/bin/env python3
"""
NETVIGIE — Test isolé de la connexion Wazuh API
Usage : python3 scripts/test_wazuh_connection.py
"""
import os
import sys
import json
import requests
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

WAZUH_URL = os.getenv("WAZUH_API_URL", "https://192.168.1.50:55000")
WAZUH_USER = os.getenv("WAZUH_API_USER", "wazuh")
WAZUH_PASS = os.getenv("WAZUH_API_PASSWORD", "wazuh")
VERIFY_SSL = os.getenv("WAZUH_API_VERIFY_SSL", "false").lower() == "true"

def test_auth():
    try:
        r = requests.post(
            f"{WAZUH_URL}/security/user/authenticate",
            auth=(WAZUH_USER, WAZUH_PASS),
            verify=VERIFY_SSL,
            timeout=10,
        )
        if r.status_code == 200:
            token = r.json().get("data", {}).get("token")
            return True, token
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, str(e)

def test_agents(token):
    try:
        r = requests.get(
            f"{WAZUH_URL}/agents",
            headers={"Authorization": f"Bearer {token}"},
            verify=VERIFY_SSL,
            timeout=10,
        )
        if r.status_code == 200:
            items = r.json().get("data", {}).get("affected_items", [])
            return True, len(items)
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    print(f"URL Wazuh : {WAZUH_URL}")
    print(f"Utilisateur : {WAZUH_USER}")
    print()

    ok, result = test_auth()
    if not ok:
        print(f"[ERREUR] Authentification Wazuh : {result}")
        return 1
    print("[OK] Authentification Wazuh réussie")
    token = result

    ok, result = test_agents(token)
    if not ok:
        print(f"[ERREUR] Récupération des agents : {result}")
        return 1
    print(f"[OK] Agents Wazuh récupérés : {result}")

    return 0

if __name__ == "__main__":
    sys.exit(main())