from fastapi import APIRouter, Depends, status

from app.api.deps import get_repositories, require_perfil
from app.appwrite.repositories import Repositories
from app.schemas.auth import (
    UsuarioCreate,
    UsuarioListResponse,
    UsuarioUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth/usuarios", tags=["Usuários"])


@router.get("", response_model=list[UsuarioListResponse])
async def listar_usuarios(
    user: dict = Depends(require_perfil("admin", "supervisor")),
    repos: Repositories = Depends(get_repositories),
):
    service = AuthService(repos)
    return await service.listar_usuarios()


@router.post("", response_model=UsuarioListResponse, status_code=status.HTTP_201_CREATED)
async def criar_usuario(
    body: UsuarioCreate,
    user: dict = Depends(require_perfil("admin", "supervisor")),
    repos: Repositories = Depends(get_repositories),
):
    service = AuthService(repos)
    return await service.criar_usuario(body.model_dump(), user)


@router.get("/{usuario_id}", response_model=UsuarioListResponse)
async def obter_usuario(
    usuario_id: str,
    user: dict = Depends(require_perfil("admin", "supervisor")),
    repos: Repositories = Depends(get_repositories),
):
    service = AuthService(repos)
    return await service.obter_usuario(usuario_id)


@router.patch("/{usuario_id}", response_model=UsuarioListResponse)
async def atualizar_usuario(
    usuario_id: str,
    body: UsuarioUpdate,
    user: dict = Depends(require_perfil("admin", "supervisor")),
    repos: Repositories = Depends(get_repositories),
):
    service = AuthService(repos)
    return await service.atualizar_usuario(usuario_id, body.model_dump(exclude_none=True), user)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_usuario(
    usuario_id: str,
    user: dict = Depends(require_perfil("admin")),
    repos: Repositories = Depends(get_repositories),
):
    service = AuthService(repos)
    await service.remover_usuario(usuario_id)
