#!/usr/bin/env bash
# ============================================================
# NETVIGIE — Sauvegarde (base + config)
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'

NETVIGIE_DIR="/home/serveurminisoc/netvigie"
BACKUP_DIR="$NETVIGIE_DIR/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/netvigie_backup_${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo -e "${GREEN}=== Sauvegarde NETVIGIE ===${NC}"

# 1. Dump PostgreSQL
echo "→ Dump PostgreSQL..."
DB_DUMP="$BACKUP_DIR/netvigie_db_${TIMESTAMP}.sql"
PGPASSWORD='Netvigie2026!' pg_dump -h 127.0.0.1 -U netvigie -d netvigie > "$DB_DUMP"
gzip "$DB_DUMP"

# 2. Archive config + DB
echo "→ Archive config..."
tar -czf "$BACKUP_FILE" \
    -C "$NETVIGIE_DIR" \
    .env \
    config/ \
    data/backups/netvigie_db_${TIMESTAMP}.sql.gz \
    frontend/.env 2>/dev/null || true

# 3. Nettoyage : garder les 10 dernières sauvegardes
echo "→ Nettoyage des anciennes sauvegardes..."
ls -t "$BACKUP_DIR"/netvigie_backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm

echo -e "${GREEN}✓ Sauvegarde créée : $BACKUP_FILE${NC}"
echo "  Taille : $(du -h "$BACKUP_FILE" | cut -f1)"