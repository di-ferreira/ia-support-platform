from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_repositories, require_perfil
from app.api.realtime import emitir_chat_atualizado
from app.appwrite.repositories import Repositories
from app.models.chat import PrioridadeChat, StatusChat
from app.schemas.auditoria import AuditoriaResponse
from app.schemas.chat import (
    ChatAssign,
    ChatCreate,
    ChatDetailResponse,
    ChatListResponse,
    ChatPrioridade,
    ChatReabrir,
    ChatTransferir,
    ChatTransferirGrupo,
    ChatUpdateStatus,
)
from app.services.auditoria_service import Ator
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chats", tags=["Chats"])


@router.get("", response_model=list[ChatListResponse])
async def listar_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: StatusChat | None = Query(None),
    cliente_id: str | None = Query(None),
    prioridade: PrioridadeChat | None = Query(None),
    departamento_id: str | None = Query(None),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    chats, _ = await service.listar(
        skip=skip,
        limit=limit,
        status=status,
        cliente_id=cliente_id,
        prioridade=prioridade,
        departamento_id=departamento_id,
        user=user,
    )
    return chats


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def obter_chat(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.obter_com_escopo(chat_id, user)


@router.get("/{chat_id}/auditoria", response_model=list[AuditoriaResponse])
async def listar_auditoria(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    """Trilha de auditoria do chat (spec 04 §Auditoria obrigatória)."""
    service = ChatService(repos)
    return await service.listar_auditoria(chat_id, user)


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
    anterior = await service.obter(chat_id)
    chat = await service.atualizar_status(chat_id, body.status, Ator.humano(user), user=user)
    await emitir_chat_atualizado(anterior, chat)
    return chat


@router.patch("/{chat_id}/confirmar-resolucao", response_model=ChatDetailResponse)
async def confirmar_resolucao(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.confirmar_resolucao(chat_id, user)


@router.patch("/{chat_id}/reabrir", response_model=ChatDetailResponse)
async def reabrir_chat(
    chat_id: str,
    body: ChatReabrir = ChatReabrir(),
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    return await service.reabrir(chat_id, user, motivo=body.motivo)


@router.patch(
    "/{chat_id}/assinar",
    response_model=ChatDetailResponse,
    deprecated=True,
)
async def assinar_chat(
    chat_id: str,
    body: ChatAssign,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    """[DEPRECATED] Assumir/atribuir um chamado.

    Use ``PATCH /chats/{id}/atribuir-atendente``, que registra ator e motivo
    (spec 04/01).
    """
    service = ChatService(repos)
    anterior = await service.obter(chat_id)
    chat = await service.assinar(chat_id, body.atendente_id, Ator.humano(user))
    await emitir_chat_atualizado(anterior, chat)
    return chat


@router.patch("/{chat_id}/prioridade", response_model=ChatDetailResponse)
async def definir_prioridade(
    chat_id: str,
    body: ChatPrioridade,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(require_perfil("admin", "supervisor")),
):
    service = ChatService(repos)
    anterior = await service.obter(chat_id)
    chat = await service.definir_prioridade(chat_id, body.prioridade, Ator.humano(user), user=user)
    await emitir_chat_atualizado(anterior, chat)
    return chat


@router.patch("/{chat_id}/pegar", response_model=ChatDetailResponse)
async def pegar_chat(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    anterior = await service.obter(chat_id)
    chat = await service.pegar(chat_id, user["id"], Ator.humano(user))
    await emitir_chat_atualizado(anterior, chat)
    return chat


@router.patch("/{chat_id}/transferir", response_model=ChatDetailResponse)
async def transferir_chat(
    chat_id: str,
    body: ChatTransferir,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    anterior = await service.obter(chat_id)
    chat = await service.transferir(chat_id, body.atendente_id, user, ator=Ator.humano(user))
    await emitir_chat_atualizado(anterior, chat)
    return chat


@router.patch("/{chat_id}/transferir-grupo", response_model=ChatDetailResponse)
async def transferir_chat_grupo(
    chat_id: str,
    body: ChatTransferirGrupo,
    repos: Repositories = Depends(get_repositories),
    user: dict = Depends(get_current_user),
):
    service = ChatService(repos)
    destino = body.departamento_id or body.setor
    return await service.transferir_grupo(chat_id, destino, user, motivo=body.motivo)
