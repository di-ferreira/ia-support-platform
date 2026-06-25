from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_session
from app.models.atendente import Atendente
from app.schemas.mensagem import MensagemCreate, MensagemResponse
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
    return await service.enviar(data)
