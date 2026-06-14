import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.session import get_db
from app.models.usuario import RolEnum, Usuario

bearer_scheme = HTTPBearer(auto_error=True)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: DbSession,
) -> Usuario:
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

    user = await db.get(Usuario, user_id)
    if user is None or not user.activo:
        raise credentials_exception

    return user


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


async def require_super_admin(current_user: CurrentUser) -> Usuario:
    """Solo permite usuarios con rol super_admin."""
    if current_user.rol != RolEnum.super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de super administrador",
        )
    return current_user


async def require_empresa_access(empresa_id: uuid.UUID, current_user: CurrentUser) -> Usuario:
    """Permite acceso si el usuario es super_admin o admin de la empresa del path."""
    if current_user.rol == RolEnum.super_admin:
        return current_user
    if (
        current_user.rol == RolEnum.admin_empresa
        and current_user.empresa_id == empresa_id
    ):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tiene acceso a los recursos de esta empresa",
    )


RequireSuperAdmin = Annotated[Usuario, Depends(require_super_admin)]
RequireEmpresaAccess = Annotated[Usuario, Depends(require_empresa_access)]
