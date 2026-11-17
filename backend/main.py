"""
NETVIGIE — Point d'entrée FastAPI (Module 7 complet)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.database import test_connection
from backend.core.logging_config import setup_logging
from backend.core.redis_bus import get_bus

from backend.api.v1 import (
    auth,
    health,
    machines,
    events,
    alerts,
    incidents,
    agents,
    stats,
)
from backend.api import websocket

logger = setup_logging("netvigie.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Démarrage NETVIGIE ({settings.app_env})")
    if not test_connection():
        logger.error("Connexion PostgreSQL échouée")
    else:
        logger.info("PostgreSQL connecté")
    if get_bus().ping():
        logger.info("Redis connecté")
    else:
        logger.error("Redis inaccessible")
    yield
    logger.info("Arrêt NETVIGIE")


app = FastAPI(
    title="NETVIGIE",
    description="Plateforme intelligente multi-agents de supervision réseau, système et cybersécurité",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
PREFIX = "/api/v1"
app.include_router(health.router, prefix=PREFIX)
app.include_router(auth.router, prefix=PREFIX)
app.include_router(machines.router, prefix=PREFIX)
app.include_router(events.router, prefix=PREFIX)
app.include_router(alerts.router, prefix=PREFIX)
app.include_router(incidents.router, prefix=PREFIX)
app.include_router(agents.router, prefix=PREFIX)
app.include_router(stats.router, prefix=PREFIX)
app.include_router(websocket.router, prefix=PREFIX)


@app.get("/")
def root():
    return {
        "app": "NETVIGIE",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }