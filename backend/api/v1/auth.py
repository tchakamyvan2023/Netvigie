"""
NETVIGIE — Endpoints Authentification
POST /auth/login, POST /auth/refresh, GET /auth/me
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from backend.api.deps import get_current_user
from backend.core.config import settings
from backend.core.database import get_db
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from backend.models.user import User
from backend.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserMe

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Compte désactivé")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access = create_access_token(subject=user.username, role=user.role)
    refresh = create_refresh_token(subject=user.username, role=user.role)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Refresh token invalide")

    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Type de token invalide")

    user = db.query(User).filter(User.username == data.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Utilisateur invalide")

    access = create_access_token(subject=user.username, role=user.role)
    refresh = create_refresh_token(subject=user.username, role=user.role)

    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserMe)
def me(current: User = Depends(get_current_user)):
    return current