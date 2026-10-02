from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_repositories
from app.appwrite.repositories import Repositories
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
async def login(
    body: LoginRequest,
    repos: Repositories = Depends(get_repositories),
):
    service = AuthService(repos)
    return await service.login(body.email, body.senha)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    repos: Repositories = Depends(get_repositories),
):
    service = AuthService(repos)
    return await service.refresh(body.refresh_token)


@router.get("/me", response_model=AtendenteResponse)
async def me(user: dict = Depends(get_current_user)):
    return user


@router.patch("/password", status_code=204)
async def alterar_senha(
    body: AlterarSenhaRequest,
    user: dict = Depends(get_current_user),
    repos: Repositories = Depends(get_repositories),
):
    service = AuthService(repos)
    await service.alterar_senha(user, body.senha_atual, body.nova_senha)
