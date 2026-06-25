from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.atendente import Atendente
from app.schemas.auth import (
    AlterarSenhaRequest,
    AtendenteResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    return await service.login(body.email, body.senha)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_session)):
    service = AuthService(session)
    return await service.refresh(body.refresh_token)


@router.get("/me", response_model=AtendenteResponse)
async def me(user: Atendente = Depends(get_current_user)):
    return user


@router.patch("/password", status_code=204)
async def alterar_senha(
    body: AlterarSenhaRequest,
    user: Atendente = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    await service.alterar_senha(user, body.senha_atual, body.nova_senha)
