#!/usr/bin/env bash
# ============================================================
# NETVIGIE — Démarrage complet
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Ce script doit être exécuté en root (sudo).${NC}"
    exit 1
fi

echo -e "${GREEN}=== Démarrage NETVIGIE ===${NC}"

# 1. Vérifier PostgreSQL et Redis
echo -n "PostgreSQL... "
systemctl is-active --quiet postgresql && echo -e "${GREEN}OK${NC}" || { echo -e "${RED}KO${NC}"; systemctl start postgresql; }
echo -n "Redis... "
systemctl is-active --quiet redis-server && echo -e "${GREEN}OK${NC}" || { echo -e "${RED}KO${NC}"; systemctl start redis-server; }

# 2. Démarrer les services NETVIGIE
systemctl start netvigie-api.service
systemctl start netvigie-agents.service
systemctl start netvigie-frontend.service
systemctl start netvigie.target

sleep 3

# 3. Vérifier
echo ""
echo -e "${GREEN}=== État des services ===${NC}"
for svc in netvigie-api netvigie-agents netvigie-frontend; do
    if systemctl is-active --quiet "${svc}.service"; then
        echo -e "  ${GREEN}✓${NC} ${svc}"
    else
        echo -e "  ${RED}✗${NC} ${svc} (voir logs)"
    fi
done

echo ""
echo -e "${GREEN}NETVIGIE démarré${NC}"
echo "  Frontend : http://192.168.1.40:3000"
echo "  API      : http://192.168.1.40:8000/docs"
echo ""
echo "Logs : sudo journalctl -u netvigie-api -f"