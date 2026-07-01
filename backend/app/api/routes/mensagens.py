from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.atendente import Atendente
from app.models.chat import Chat
from app.models.mensagem import RemetenteMensagem
from app.schemas.mensagem import MensagemCreate, MensagemResponse
from app.services.evolution_service import EvolutionService
from app.services.mensagem_service import MensagemService

router = APIRouter(prefix="/chats/{chat_id}/mensagens", tags=["Mensagens"])


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

    return mensagem
