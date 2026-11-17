#!/usr/bin/env bash
# ============================================================
# NETVIGIE — Installation des services systemd
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Ce script doit être exécuté en root (sudo).${NC}"
    exit 1
fi

NETVIGIE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SYSTEMD_SRC="$NETVIGIE_DIR/systemd"

echo -e "${GREEN}=== Installation des services systemd ===${NC}"

# Vérifier que les fichiers existent
for f in netvigie-api.service netvigie-agents.service netvigie-frontend.service netvigie.target; do
    if [[ ! -f "$SYSTEMD_SRC/$f" ]]; then
        echo -e "${RED}✗ Fichier manquant : $SYSTEMD_SRC/$f${NC}"
        exit 1
    fi
done

# Copier
cp "$SYSTEMD_SRC"/*.service /etc/systemd/system/
cp "$SYSTEMD_SRC/netvigie.target" /etc/systemd/system/

# Recharger
systemctl daemon-reload

# Activer au boot
systemctl enable netvigie.target
systemctl enable netvigie-api.service
systemctl enable netvigie-agents.service
systemctl enable netvigie-frontend.service

echo -e "${GREEN}✓ Services installés et activés${NC}"
echo ""
echo "Commandes utiles :"
echo "  sudo systemctl start netvigie.target    # Démarrer"
echo "  sudo systemctl stop netvigie.target     # Arrêter"
echo "  sudo systemctl restart netvigie.target  # Redémarrer"
echo "  sudo systemctl status netvigie.target   # État"
echo "  sudo journalctl -u netvigie-api -f      # Logs API"