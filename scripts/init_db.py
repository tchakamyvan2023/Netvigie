#!/usr/bin/env python3
"""
NETVIGIE — Initialisation de la base de données
Crée les tables + l'utilisateur admin + les 4 agents NETVIGIE.
Applique les migrations manquantes (ALTER TABLE) pour les tables existantes.
Idempotent : peut être relancé sans risque.
"""
import sys
from pathlib import Path

# Ajouter le projet au PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text

from backend.core.config import settings
from backend.core.database import init_db, db_session, engine
from backend.core.security import hash_password
from backend.models.user import User
from backend.models.agent_netvigie import AgentNetvigie


NETVIGIE_AGENTS = [
    "collector",
    "diagnostic",
    "security",
    "correlation",
]


# ---------------------------------------------------------------------------
# Migrations manuelles (ALTER TABLE) pour les tables existantes
# ---------------------------------------------------------------------------
def apply_migrations():
    """
    Applique les migrations nécessaires aux tables existantes.
    `create_all()` ne modifie pas les tables existantes, donc on ajoute
    les colonnes manquantes via ALTER TABLE.
    """
    migrations = [
        # Table alerts (Module 5)
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMPTZ",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS security_category VARCHAR(64)",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS risk_score DOUBLE PRECISION",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS pattern_detected BOOLEAN NOT NULL DEFAULT FALSE",
        "CREATE INDEX IF NOT EXISTS ix_alerts_analyzed ON alerts(analyzed_at)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_category ON alerts(security_category)",

        # Table incidents (Module 6)
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS proposed_action VARCHAR(128)",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS action_target VARCHAR(128)",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS evidence_json JSONB",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS alert_ids_json JSONB",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS event_ids_json JSONB",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS machine_ids_json JSONB",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(64)",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS closed_by VARCHAR(64)",
        "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS resolution_notes TEXT",

        # Table machines (Module 3-4)
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS latency_ms DOUBLE PRECISION",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS packet_loss_percent DOUBLE PRECISION",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS last_ping_at TIMESTAMPTZ",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS is_excluded BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS role VARCHAR(64)",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS criticality VARCHAR(32)",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS display_name VARCHAR(255)",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS last_sync TIMESTAMPTZ NOT NULL DEFAULT NOW()",

        # Table agents_netvigie (Module 3)
        "ALTER TABLE agents_netvigie ADD COLUMN IF NOT EXISTS events_processed INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE agents_netvigie ADD COLUMN IF NOT EXISTS errors_count INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE agents_netvigie ADD COLUMN IF NOT EXISTS avg_processing_ms DOUBLE PRECISION NOT NULL DEFAULT 0",
        "ALTER TABLE agents_netvigie ADD COLUMN IF NOT EXISTS last_error TEXT",
        "ALTER TABLE agents_netvigie ADD COLUMN IF NOT EXISTS config_json TEXT",
    ]

    applied = 0
    with engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
                applied += 1
            except Exception as e:
                # Ignorer les erreurs "already exists" (PostgreSQL)
                msg = str(e).lower()
                if "already exists" in msg or "duplicate column" in msg:
                    continue
                print(f"[init_db] ⚠ Migration échouée : {sql[:60]}... — {str(e)[:100]}")

    print(f"[init_db] {applied} migration(s) appliquée(s) (les autres étaient déjà présentes)")


# ---------------------------------------------------------------------------
# Création de l'admin
# ---------------------------------------------------------------------------
def create_admin():
    with db_session() as db:
        existing = db.query(User).filter(User.username == settings.admin_username).first()
        if existing:
            print(f"[init_db] Admin '{settings.admin_username}' déjà présent")
            return
        admin = User(
            username=settings.admin_username,
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        print(f"[init_db] Admin '{settings.admin_username}' créé")


# ---------------------------------------------------------------------------
# Création des 4 agents NETVIGIE
# ---------------------------------------------------------------------------
def create_agents():
    with db_session() as db:
        for name in NETVIGIE_AGENTS:
            existing = db.query(AgentNetvigie).filter(AgentNetvigie.name == name).first()
            if existing:
                print(f"[init_db] Agent '{name}' déjà présent")
                continue
            agent = AgentNetvigie(name=name, status="stopped")
            db.add(agent)
            print(f"[init_db] Agent '{name}' créé")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  NETVIGIE — Initialisation de la base de données")
    print("=" * 60)

    print("\n[1/4] Création des tables (create_all)...")
    init_db()
    print("[init_db] Tables créées (ou déjà existantes)")

    print("\n[2/4] Application des migrations...")
    apply_migrations()

    print("\n[3/4] Création de l'admin...")
    create_admin()

    print("\n[4/4] Création des 4 agents NETVIGIE...")
    create_agents()

    print("\n" + "=" * 60)
    print("  ✅ Initialisation terminée")
    print("=" * 60)


if __name__ == "__main__":
    main()