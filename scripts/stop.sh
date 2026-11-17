#!/usr/bin/env bash
# ============================================================
# NETVIGIE — Arrêt complet
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}Ce script doit être exécuté en root (sudo).${NC}"
    exit 1
fi

echo -e "${GREEN}=== Arrêt NETVIGIE ===${NC}"

systemctl stop netvigie.target || true
systemctl stop netvigie-frontend.service || true
systemctl stop netvigie-agents.service || true
systemctl stop netvigie-api.service || true

echo -e "${GREEN}NETVIGIE arrêté${NC}"