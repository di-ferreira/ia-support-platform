from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_perfil
from app.core.database import get_session
from app.models.atendente import Atendente
from app.models.knowledge_base import CategoriaConhecimento
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from app.services.knowledge_base_service import KnowledgeBaseService

router = APIRouter(prefix="/knowledge-base", tags=["Base de Conhecimento"])


@router.get("", response_model=list[KnowledgeBaseResponse])
async def listar_artigos(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    categoria: CategoriaConhecimento | None = Query(None),
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = KnowledgeBaseService(session)
    artigos, _ = await service.listar(skip, limit, categoria)
    return artigos


@router.get("/{artigo_id}", response_model=KnowledgeBaseResponse)
async def obter_artigo(
    artigo_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = KnowledgeBaseService(session)
    return await service.obter(artigo_id)


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def criar_artigo(
    body: KnowledgeBaseCreate,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
):
    service = KnowledgeBaseService(session)
    return await service.criar(body.model_dump())


@router.patch("/{artigo_id}", response_model=KnowledgeBaseResponse)
async def atualizar_artigo(
    artigo_id: int,
    body: KnowledgeBaseUpdate,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
):
    service = KnowledgeBaseService(session)
    return await service.atualizar(artigo_id, body.model_dump(exclude_none=True))


@router.delete("/{artigo_id}", status_code=204)
async def remover_artigo(
    artigo_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
):
    service = KnowledgeBaseService(session)
    await service.remover(artigo_id)
