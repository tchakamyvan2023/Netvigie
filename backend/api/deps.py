"""
NETVIGIE — Dépendances FastAPI
Auth JWT, session DB, pagination, RBAC.
"""
from typing import Optional

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import decode_token, has_permission
from backend.models.user import User
from backend.schemas.common import PaginationParams

# Schéma de sécurité HTTP Bearer
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Valide le JWT et retourne l'utilisateur courant."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Type de token invalide",
        )

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token sans sujet")

    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur inactif ou inexistant")

    return user


def require_permission(permission: str):
    """Factory de dépendance pour vérifier une permission RBAC."""
    def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission refusée : {permission}",
            )
        return user
    return checker


def get_pagination(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)