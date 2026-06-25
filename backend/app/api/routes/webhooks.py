from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.webhook import (
    WebhookContexto,
    WebhookDiagnostico,
    WebhookMensagem,
    WebhookStatusUpdate,
)
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks (n8n)"])


@router.post("/mensagem", status_code=201)
async def webhook_mensagem(
    body: WebhookMensagem,
    session: AsyncSession = Depends(get_session),
):
    service = WebhookService(session)
    return await service.receber_mensagem(body.model_dump())


@router.patch("/chat/status")
async def webhook_status(
    body: WebhookStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    service = WebhookService(session)
    return await service.atualizar_status(body.chat_id, body.status)


@router.post("/chat/diagnostico")
async def webhook_diagnostico(
    body: WebhookDiagnostico,
    session: AsyncSession = Depends(get_session),
):
    service = WebhookService(session)
    return await service.salvar_diagnostico(body.model_dump())


@router.get("/chat/{chat_id}/contexto", response_model=WebhookContexto)
async def webhook_contexto(
    chat_id: int,
    session: AsyncSession = Depends(get_session),
):
    service = WebhookService(session)
    contexto = await service.obter_contexto(chat_id)
    if not contexto:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
        )
    return contexto
