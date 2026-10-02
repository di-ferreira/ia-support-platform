from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_repositories, require_perfil
from app.appwrite.repositories import Repositories
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
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = KnowledgeBaseService(repos)
    artigos, _ = await service.listar(skip, limit, categoria)
    return artigos


@router.get("/{artigo_id}", response_model=KnowledgeBaseResponse)
async def obter_artigo(
    artigo_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = KnowledgeBaseService(repos)
    return await service.obter(artigo_id)


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
async def criar_artigo(
    body: KnowledgeBaseCreate,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    service = KnowledgeBaseService(repos)
    return await service.criar(body.model_dump())


@router.patch("/{artigo_id}", response_model=KnowledgeBaseResponse)
async def atualizar_artigo(
    artigo_id: str,
    body: KnowledgeBaseUpdate,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    service = KnowledgeBaseService(repos)
    return await service.atualizar(artigo_id, body.model_dump(exclude_none=True))


@router.delete("/{artigo_id}", status_code=204)
async def remover_artigo(
    artigo_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    service = KnowledgeBaseService(repos)
    await service.remover(artigo_id)
