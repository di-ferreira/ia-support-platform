from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_perfil
from app.core.database import get_session
from app.models.atendente import Atendente
from app.models.chat import PrioridadeChat, StatusChat
from app.models.mensagem import Mensagem
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
    cliente_id: int | None = Query(None),
    prioridade: PrioridadeChat | None = Query(None),
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ChatService(session)
    chats, _ = await service.listar(skip, limit, status, cliente_id, prioridade, user)

    last_msg_map: dict[int, str | None] = {}
    if chats:
        chat_ids = [c.id for c in chats]
        subq = (
            select(Mensagem.chat_id, func.max(Mensagem.id).label("max_id"))
            .where(Mensagem.chat_id.in_(chat_ids))
            .group_by(Mensagem.chat_id)
        ).subquery()
        rows = await session.execute(
            select(Mensagem).join(subq, Mensagem.id == subq.c.max_id)
        )
        last_msg_map = {m.chat_id: m.conteudo for m in rows.scalars().all()}

    result = []
    for chat in chats:
        result.append(
            {
                "id": chat.id,
                "cliente_id": chat.cliente_id,
                "cliente_nome": chat.cliente.nome if chat.cliente else None,
                "status": chat.status,
                "prioridade": chat.prioridade,
                "resumo_problema": chat.resumo_problema,
                "solucao_sugerida_ia": chat.solucao_sugerida_ia,
                "nivel_confianca_ia": chat.nivel_confianca_ia,
                "necessita_humano": chat.necessita_humano,
                "atendente_id": chat.atendente_id,
                "setor_alvo": chat.setor_alvo,
                "ultima_mensagem_em": chat.ultima_mensagem_em,
                "ultima_mensagem": last_msg_map.get(chat.id),
                "created_at": chat.created_at,
            }
        )
    return result


@router.get("/{chat_id}", response_model=ChatDetailResponse)
async def obter_chat(
    chat_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ChatService(session)
    return await service.obter(chat_id)


@router.post("", response_model=ChatDetailResponse, status_code=201)
async def criar_chat(
    body: ChatCreate,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ChatService(session)
    return await service.criar(body.model_dump())


@router.patch("/{chat_id}/status", response_model=ChatDetailResponse)
async def atualizar_status(
    chat_id: int,
    body: ChatUpdateStatus,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ChatService(session)
    return await service.atualizar_status(chat_id, body.status)


@router.patch("/{chat_id}/assinar", response_model=ChatDetailResponse)
async def assinar_chat(
    chat_id: int,
    body: ChatAssign,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
):
    service = ChatService(session)
    return await service.assinar(chat_id, body.atendente_id)


@router.patch("/{chat_id}/prioridade", response_model=ChatDetailResponse)
async def definir_prioridade(
    chat_id: int,
    body: ChatPrioridade,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(require_perfil("admin", "supervisor")),
):
    service = ChatService(session)
    return await service.definir_prioridade(chat_id, body.prioridade)


@router.patch("/{chat_id}/pegar", response_model=ChatDetailResponse)
async def pegar_chat(
    chat_id: int,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ChatService(session)
    return await service.pegar(chat_id, user.id)


@router.patch("/{chat_id}/transferir", response_model=ChatDetailResponse)
async def transferir_chat(
    chat_id: int,
    body: ChatTransferir,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ChatService(session)
    return await service.transferir(chat_id, body.atendente_id, user)


@router.patch("/{chat_id}/transferir-grupo", response_model=ChatDetailResponse)
async def transferir_chat_grupo(
    chat_id: int,
    body: ChatTransferirGrupo,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = ChatService(session)
    return await service.transferir_grupo(chat_id, body.setor, user)
