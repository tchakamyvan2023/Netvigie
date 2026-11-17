#!/usr/bin/env bash
# ============================================================
# NETVIGIE — État complet
# ============================================================
set -uo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo "============================================================"
echo "  NETVIGIE — État"
echo "============================================================"

# Services systemd
echo ""
echo "Services systemd :"
for svc in postgresql redis-server netvigie-api netvigie-agents netvigie-frontend; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $svc"
    else
        echo -e "  ${RED}✗${NC} $svc"
    fi
done

# Processus
echo ""
echo "Processus :"
for p in run_agents uvicorn "npm run preview" vite; do
    if pgrep -f "$p" > /dev/null; then
        echo -e "  ${GREEN}✓${NC} $p ($(pgrep -f "$p" | head -1))"
    else
        echo -e "  ${RED}✗${NC} $p"
    fi
done

# API
echo ""
echo "API FastAPI :"
API=$(curl -s --max-time 3 http://127.0.0.1:8000/api/v1/health 2>/dev/null || echo "")
if [[ -n "$API" ]]; then
    STATUS=$(echo "$API" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null || echo "?")
    if [[ "$STATUS" == "ok" ]]; then
        echo -e "  ${GREEN}✓${NC} Health: $STATUS"
    else
        echo -e "  ${YELLOW}⚠${NC} Health: $STATUS"
    fi
else
    echo -e "  ${RED}✗${NC} Injoignable"
fi

# Wazuh
echo ""
echo "Wazuh :"
WAZUH=$(curl -sk --max-time 3 -u wazuh:wazuh https://192.168.1.50:55000/security/user/authenticate 2>/dev/null || echo "")
if [[ -n "$WAZUH" ]]; then
    echo -e "  ${GREEN}✓${NC} API accessible"
else
    echo -e "  ${RED}✗${NC} API inaccessible"
fi

# Base de données
echo ""
echo "Base de données :"
if [[ -f /home/serveurminisoc/netvigie/.env ]]; then
    DB_COUNT=$(PGPASSWORD='Netvigie2026!' psql -h 127.0.0.1 -U netvigie -d netvigie -tAc "SELECT COUNT(*) FROM machines;" 2>/dev/null || echo "0")
    echo -e "  ${GREEN}✓${NC} Machines en base : $DB_COUNT"
    INC_COUNT=$(PGPASSWORD='Netvigie2026!' psql -h 127.0.0.1 -U netvigie -d netvigie -tAc "SELECT COUNT(*) FROM incidents;" 2>/dev/null || echo "0")
    echo -e "  ${GREEN}✓${NC} Incidents en base : $INC_COUNT"
fi

# Ports
echo ""
echo "Ports en écoute :"
ss -tlnp 2>/dev/null | grep -E ":(3000|8000|5432|6379)\b" | awk '{print "  " $4}' || true

echo ""
echo "============================================================"