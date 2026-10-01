from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perfil
from app.core.database import get_session
from app.models.atendente import Atendente
from app.schemas.auth import (
    UsuarioCreate,
    UsuarioListResponse,
    UsuarioUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth/usuarios", tags=["Usuários"])


@router.get("", response_model=list[UsuarioListResponse])
async def listar_usuarios(
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    return await service.listar_usuarios()


@router.post("", response_model=UsuarioListResponse, status_code=status.HTTP_201_CREATED)
async def criar_usuario(
    body: UsuarioCreate,
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    return await service.criar_usuario(body.model_dump(), user)


@router.get("/{usuario_id}", response_model=UsuarioListResponse)
async def obter_usuario(
    usuario_id: int,
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    return await service.obter_usuario(usuario_id)


@router.patch("/{usuario_id}", response_model=UsuarioListResponse)
async def atualizar_usuario(
    usuario_id: int,
    body: UsuarioUpdate,
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    return await service.atualizar_usuario(usuario_id, body.model_dump(exclude_none=True), user)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_usuario(
    usuario_id: int,
    user: Atendente = Depends(require_perfil("admin")),
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    await service.remover_usuario(usuario_id)
