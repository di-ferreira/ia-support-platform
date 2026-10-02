from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_repositories, require_perfil
from app.appwrite.repositories import Repositories
from app.models.chat import PrioridadeChat, StatusChat
from app.schemas.chat import (
    ChatAssign,
    ChatCreate,
    ChatDetailResponse,
    ChatListResponse,
    ChatPrioridade,
    ChatTransferir,
    ChatTransferirGrupo,
    ChatUpdateStatus,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get("", response_model=list[ChatListResponse])
async def listar_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: StatusChat | None = Query(None),
    cliente_id: str | None = Query(None),
    prioridade: PrioridadeChat | None = Query(None),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    chats, _ = await service.listar(skip, limit, status, cliente_id, prioridade, user)
    return chats


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def obter_chat(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.obter(chat_id)


@router.post("", response_model=ChatDetailResponse, status_code=201)
async def criar_chat(
    body: ChatCreate,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.criar(body.model_dump())


@router.patch("/{chat_id}/status", response_model=ChatDetailResponse)
async def atualizar_status(
    chat_id: str,
    body: ChatUpdateStatus,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.atualizar_status(chat_id, body.status)


@router.patch("/{chat_id}/assinar", response_model=ChatDetailResponse)
async def assinar_chat(
    chat_id: str,
    body: ChatAssign,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    service = ChatService(repos)
    return await service.assinar(chat_id, body.atendente_id)


@router.patch("/{chat_id}/prioridade", response_model=ChatDetailResponse)
async def definir_prioridade(
    chat_id: str,
    body: ChatPrioridade,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    service = ChatService(repos)
    return await service.definir_prioridade(chat_id, body.prioridade)


@router.patch("/{chat_id}/pegar", response_model=ChatDetailResponse)
async def pegar_chat(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.pegar(chat_id, user["id"])


@router.patch("/{chat_id}/transferir", response_model=ChatDetailResponse)
async def transferir_chat(
    chat_id: str,
    body: ChatTransferir,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.transferir(chat_id, body.atendente_id, user)


@router.patch("/{chat_id}/transferir-grupo", response_model=ChatDetailResponse)
async def transferir_chat_grupo(
    chat_id: str,
    body: ChatTransferirGrupo,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.transferir_grupo(chat_id, body.setor, user)
