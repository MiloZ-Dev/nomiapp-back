import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.user import RoleEnum, User

bearer_scheme = HTTPBearer(auto_error=True)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise credentials_exception

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise credentials_exception

    sub = payload.get("sub")
    if not sub:
        raise credentials_exception

    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError):
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None or not user.active:
        raise credentials_exception

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_super_admin(current_user: CurrentUser) -> User:
    """Only allows users with the super_admin role."""
    if current_user.role != RoleEnum.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de super administrador",
        )
    return current_user


async def require_company_access(company_id: uuid.UUID, current_user: CurrentUser) -> User:
    """Allows access if the user is super_admin or admin of the path's company."""
    if current_user.role == RoleEnum.super_admin:
        return current_user
    if (
        current_user.role == RoleEnum.company_admin
        and current_user.company_id == company_id
    ):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tiene acceso a los recursos de esta empresa",
    )


RequireSuperAdmin = Annotated[User, Depends(require_super_admin)]
RequireCompanyAccess = Annotated[User, Depends(require_company_access)]
