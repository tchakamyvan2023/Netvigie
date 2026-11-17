#!/usr/bin/env bash
# ============================================================
# NETVIGIE — Mise à jour sans perte de données
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Ce script doit être exécuté en root (sudo).${NC}"
    exit 1
fi

NETVIGIE_DIR="/home/serveurminisoc/netvigie"
cd "$NETVIGIE_DIR"

echo -e "${GREEN}=== Mise à jour NETVIGIE ===${NC}"

# 1. Sauvegarde préalable
echo -e "${YELLOW}→ Sauvegarde préalable...${NC}"
bash scripts/backup.sh

# 2. Arrêt
echo -e "${YELLOW}→ Arrêt des services...${NC}"
systemctl stop netvigie.target || true
sleep 2

# 3. Git pull (si dépôt git)
if [[ -d .git ]]; then
    echo -e "${YELLOW}→ git pull...${NC}"
    git pull || echo "Pas de dépôt git ou pull impossible"
fi

# 4. Dépendances Python
echo -e "${YELLOW}→ Mise à jour des dépendances Python...${NC}"
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 5. Dépendances frontend
if [[ -d frontend ]]; then
    echo -e "${YELLOW}→ Mise à jour des dépendances frontend...${NC}"
    cd frontend
    npm install
    npm run build
    cd ..
fi

# 6. Migrations DB (si Alembic)
if [[ -d backend/migrations ]]; then
    echo -e "${YELLOW}→ Migrations DB...${NC}"
    ./venv/bin/alembic upgrade head || echo "Alembic absent ou migration échouée"
fi

# 7. Redémarrage
echo -e "${YELLOW}→ Redémarrage...${NC}"
systemctl daemon-reload
systemctl start netvigie.target
systemctl start netvigie-api.service netvigie-agents.service netvigie-frontend.service

sleep 3

echo ""
echo -e "${GREEN}=== Mise à jour terminée ===${NC}"
bash scripts/status.sh