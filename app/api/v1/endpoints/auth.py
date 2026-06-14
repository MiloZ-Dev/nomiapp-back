from fastapi import APIRouter

from app.api.responses import envelope
from app.core.dependencies import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UsuarioOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(payload: LoginRequest, db: DbSession):
    tokens: TokenResponse = await auth_service.authenticate(db, payload)
    return envelope(data=tokens, message="Inicio de sesión exitoso")


@router.post("/refresh")
async def refresh(payload: RefreshRequest, db: DbSession):
    tokens: TokenResponse = await auth_service.refresh_access_token(
        db, payload.refresh_token
    )
    return envelope(data=tokens, message="Token renovado")


@router.get("/me")
async def me(current_user: CurrentUser):
    return envelope(
        data=UsuarioOut.model_validate(current_user),
        message="Usuario actual",
    )
