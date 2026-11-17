"""NETVIGIE — Endpoints /health"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.core.config import settings
from backend.core.database import get_db
from backend.core.redis_bus import get_bus

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health(db: Session = Depends(get_db)):
    """Santé globale de NETVIGIE."""
    services = {}

    # PostgreSQL
    try:
        db.execute(text("SELECT 1"))
        services["postgresql"] = "ok"
    except Exception as e:
        services["postgresql"] = f"error: {e}"

    # Redis
    try:
        bus = get_bus()
        services["redis"] = "ok" if bus.ping() else "error"
    except Exception as e:
        services["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in services.values())

    return {
        "status": "ok" if all_ok else "degraded",
        "version": "1.0.0",
        "app": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": services,
    }


@router.get("/wazuh")
def health_wazuh():
    """Santé de la connexion Wazuh."""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        r = requests.post(
            f"{settings.wazuh_api_url}/security/user/authenticate",
            auth=(settings.wazuh_api_user, settings.wazuh_api_password),
            verify=settings.wazuh_api_verify_ssl,
            timeout=5,
        )
        if r.status_code == 200:
            return {
                "status": "ok",
                "wazuh_url": settings.wazuh_api_url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "status": "error",
            "http_code": r.status_code,
            "message": r.text[:200],
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}