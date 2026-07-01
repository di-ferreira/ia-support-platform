from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.websocket_manager import manager
from app.core.database import get_session
from app.models.atendente import Atendente
from app.models.chat import Chat, StatusChat
from app.models.cliente import Cliente
from app.models.mensagem import RemetenteMensagem
from app.schemas.mensagem import EnviarWhatsAppRequest, EnviarWhatsAppResponse, MensagemCreate, MensagemResponse
from app.services.evolution_service import EvolutionService
from app.services.mensagem_service import MensagemService

router = APIRouter(prefix="/chats/{chat_id}/mensagens", tags=["Mensagens"])
whatsapp_router = APIRouter(prefix="/chats", tags=["WhatsApp"])


@router.get("", response_model=list[MensagemResponse])
async def listar_mensagens(
    chat_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = MensagemService(session)
    return await service.listar(chat_id, skip, limit)


@router.post("", response_model=MensagemResponse, status_code=201)
async def enviar_mensagem(
    chat_id: int,
    body: MensagemCreate,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    service = MensagemService(session)
    data = body.model_dump()
    data["chat_id"] = chat_id
    mensagem = await service.enviar(data)

    if body.remetente == RemetenteMensagem.atendente:
        result = await session.execute(select(Chat).where(Chat.id == chat_id))
        chat = result.scalar_one_or_none()
        if chat and chat.whatsapp_number:
            try:
                evolution = EvolutionService()
                await evolution.enviar_texto(
                    instance_name="emsoft-support",
                    number=chat.whatsapp_number,
                    text=body.conteudo or "",
                )
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Mensagem salva, mas erro ao enviar via WhatsApp: {e}",
                )

    await manager.send_event(
        chat_id, "nova_mensagem",
        {"chat_id": chat_id, "mensagem_id": mensagem.id},
    )

    return mensagem


@whatsapp_router.post("/enviar-whatsapp", response_model=EnviarWhatsAppResponse, status_code=201)
async def enviar_whatsapp(
    body: EnviarWhatsAppRequest,
    session: AsyncSession = Depends(get_session),
    user: Atendente = Depends(get_current_user),
):
    result = await session.execute(
        select(Cliente).where(Cliente.telefone == body.numero)
    )
    cliente = result.scalar_one_or_none()
    if not cliente:
        cliente = Cliente(
            nome=f"Novo {body.numero[-8:]}",
            documento=body.numero,
            telefone=body.numero,
        )
        session.add(cliente)
        await session.flush()

    result = await session.execute(
        select(Chat)
        .where(Chat.cliente_id == cliente.id)
        .where(Chat.status.notin_([StatusChat.encerrado, StatusChat.resolvido]))
        .order_by(Chat.created_at.desc())
    )
    chat = result.scalar_one_or_none()
    if not chat:
        chat = Chat(cliente_id=cliente.id, whatsapp_number=body.numero)
        session.add(chat)
        await session.flush()

    service = MensagemService(session)
    mensagem = await service.enviar({
        "chat_id": chat.id,
        "remetente": RemetenteMensagem.atendente,
        "tipo": "texto",
        "conteudo": body.conteudo,
    })

    try:
        evolution = EvolutionService()
        await evolution.enviar_texto(
            instance_name="emsoft-support",
            number=body.numero,
            text=body.conteudo,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mensagem salva, mas erro ao enviar via WhatsApp: {e}",
        )

    await manager.send_event(
        chat.id, "nova_mensagem",
        {"chat_id": chat.id, "mensagem_id": mensagem.id},
    )

    return EnviarWhatsAppResponse(chat_id=chat.id, mensagem_id=mensagem.id)
