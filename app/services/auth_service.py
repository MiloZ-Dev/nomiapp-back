import uuid

import jwt
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse


async def authenticate(db: AsyncSession, payload: LoginRequest) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == payload.email.lower())
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token inválido o expirado",
    )

    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError:
        raise invalid

    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise invalid

    sub = payload.get("sub")
    if not sub:
        raise invalid

    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        raise invalid

    user = await db.get(User, user_id)
    if user is None or not user.active:
        raise invalid

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
