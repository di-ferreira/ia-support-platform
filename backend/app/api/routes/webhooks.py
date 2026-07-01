from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.websocket_manager import manager
from app.core.database import get_session
from app.schemas.webhook import (
    WebhookClienteUpdate,
    WebhookContexto,
    WebhookDiagnostico,
    WebhookMensagem,
    WebhookStatusUpdate,
)
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks (n8n)"])


def _normalizar_payload(body: dict) -> dict:
    whatsapp = body.get("whatsapp_number")
    conteudo = body.get("conteudo")
    if whatsapp:
        return body

    data = body.get("data") or {}
    key = data.get("key") or {}
    message = data.get("message") or {}

    remote_jid = key.get("remoteJid", "")
    if remote_jid:
        content = (
            message.get("conversation")
            or (message.get("extendedTextMessage") or {}).get("text")
            or ""
        )
        return {"whatsapp_number": remote_jid, "conteudo": content}

    return body


@router.post("/mensagem", status_code=201)
async def webhook_mensagem(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    body = await request.json()
    payload = _normalizar_payload(body)
    validated = WebhookMensagem(**payload)
    service = WebhookService(session)
    mensagem = await service.receber_mensagem(validated.model_dump())
    await manager.send_event(
        mensagem.chat_id, "nova_mensagem",
        {"chat_id": mensagem.chat_id, "mensagem_id": mensagem.id},
    )
    return mensagem


@router.patch("/chat/status")
async def webhook_status(
    body: WebhookStatusUpdate,
    session: AsyncSession = Depends(get_session),
):
    service = WebhookService(session)
    chat = await service.atualizar_status(body.chat_id, body.status)
    await manager.send_event(
        body.chat_id, "status_update",
        {"chat_id": body.chat_id, "status": body.status.value},
    )
    return chat


@router.post("/chat/diagnostico")
async def webhook_diagnostico(
    body: WebhookDiagnostico,
    session: AsyncSession = Depends(get_session),
):
    service = WebhookService(session)
    diagnostico = await service.salvar_diagnostico(body.model_dump())
    await manager.send_event(
        body.chat_id, "diagnostico",
        {"chat_id": body.chat_id, "diagnostico_id": diagnostico.id},
    )
    return diagnostico


@router.patch("/cliente/{chat_id}")
async def webhook_atualizar_cliente(
    chat_id: int,
    body: WebhookClienteUpdate,
    session: AsyncSession = Depends(get_session),
):
    service = WebhookService(session)
    return await service.atualizar_cliente(chat_id, body.model_dump(exclude_none=True))


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
