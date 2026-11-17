"""
NETVIGIE — Sécurité : JWT, bcrypt, RBAC
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Mots de passe ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


# --- JWT ---
def create_access_token(
    subject: str,
    role: str = "viewer",
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, role: str = "viewer") -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": subject,
        "role": role,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Dict[str, Any]:
    """Lève JWTError si invalide ou expiré."""
    return jwt.decode(
        token, settings.app_secret_key, algorithms=[settings.jwt_algorithm]
    )


# --- RBAC ---
ROLES = {
    "admin": {"can_manage_users", "can_manage_incidents", "can_view_all"},
    "analyst": {"can_manage_incidents", "can_view_all"},
    "viewer": {"can_view_all"},
}


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLES.get(role, set())