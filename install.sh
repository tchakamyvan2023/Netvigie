#!/usr/bin/env bash
# ============================================================
# NETVIGIE — Wrapper d'installation
# Usage : sudo bash install.sh
# ============================================================
set -euo pipefail

cd "$(dirname "$0")"

if [[ $EUID -ne 0 ]]; then
    echo "Ce script doit être exécuté en root (sudo)."
    exit 1
fi

# Vérifier Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 introuvable. Installez-le d'abord."
    exit 1
fi

exec python3 bootstrap.py "$@"