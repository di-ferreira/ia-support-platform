import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_repositories
from app.api.websocket_manager import manager
from app.appwrite.repositories import Repositories
from app.core.config import settings
from app.schemas.webhook import (
    WebhookClienteUpdate,
    WebhookContexto,
    WebhookDiagnostico,
    WebhookMensagem,
    WebhookSolucaoRequest,
    WebhookSolucaoResponse,
    WebhookStatusUpdate,
)
from app.services.ai_pipeline import AIPipelineService
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks (n8n)"])


async def verify_webhook(request: Request) -> None:
    secret = settings.webhook_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook não configurado",
        )
    provided = request.headers.get("X-Webhook-Secret")
    if not provided or not hmac.compare_digest(provided, secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assinatura inválida",
        )


def _normalizar_payload(body: dict) -> dict:
    whatsapp = body.get("whatsapp_number")
    remetente = body.get("remetente")

    if whatsapp:
        result = dict(body)
        if "chat_id" in result:
            if result["chat_id"] is None:
                del result["chat_id"]
            else:
                result["chat_id"] = str(result["chat_id"])
        return result

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
        result = {"whatsapp_number": remote_jid, "conteudo": content}
        if remetente:
            result["remetente"] = remetente
        return result

    return body


@router.post("/mensagem", status_code=201)
async def webhook_mensagem(
    request: Request,
    repos: Repositories = Depends(get_repositories),
    webhook_auth: None = Depends(verify_webhook),
):
    body = await request.json()
    payload = _normalizar_payload(body)
    validated = WebhookMensagem(**payload)
    service = WebhookService(repos)
    mensagem = await service.receber_mensagem(validated.model_dump())
    await manager.send_event(
        mensagem["chat_id"], "nova_mensagem",
        {"chat_id": mensagem["chat_id"], "mensagem_id": mensagem["id"]},
    )
    return mensagem


@router.patch("/chat/status")
async def webhook_status(
    body: WebhookStatusUpdate,
    repos: Repositories = Depends(get_repositories),
    webhook_auth: None = Depends(verify_webhook),
):
    service = WebhookService(repos)
    chat = await service.atualizar_status(body.chat_id, body.status)
    await manager.send_event(
        body.chat_id, "status_update",
        {"chat_id": body.chat_id, "status": body.status.value},
    )
    return chat


@router.post("/chat/diagnostico")
async def webhook_diagnostico(
    body: WebhookDiagnostico,
    repos: Repositories = Depends(get_repositories),
    webhook_auth: None = Depends(verify_webhook),
):
    service = WebhookService(repos)
    diagnostico = await service.salvar_diagnostico(body.model_dump())
    await manager.send_event(
        body.chat_id, "diagnostico",
        {"chat_id": body.chat_id, "diagnostico_id": diagnostico["id"]},
    )
    return diagnostico


@router.post("/ai/solucionar", response_model=WebhookSolucaoResponse)
async def webhook_ai_solucionar(
    body: WebhookSolucaoRequest,
    repos: Repositories = Depends(get_repositories),
    webhook_auth: None = Depends(verify_webhook),
):
    service = AIPipelineService(repos)
    return await service.solucionar(body.chat_id)


@router.patch("/cliente/{chat_id}")
async def webhook_atualizar_cliente(
    chat_id: str,
    body: WebhookClienteUpdate,
    repos: Repositories = Depends(get_repositories),
    webhook_auth: None = Depends(verify_webhook),
):
    service = WebhookService(repos)
    return await service.atualizar_cliente(chat_id, body.model_dump(exclude_none=True))


@router.get("/chat/{chat_id}/contexto", response_model=WebhookContexto)
async def webhook_contexto(
    chat_id: str,
    repos: Repositories = Depends(get_repositories),
    webhook_auth: None = Depends(verify_webhook),
):
    service = WebhookService(repos)
    contexto = await service.obter_contexto(chat_id)
    if not contexto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat não encontrado"
        )
    return contexto
