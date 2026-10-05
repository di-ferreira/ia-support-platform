import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

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


def _extrair_mensagem_bruta(message: dict) -> tuple[str | None, str, str | None]:
    """Deriva (conteudo, tipo, url_arquivo) do bloco `message` do payload bruto."""
    if message.get("conversation"):
        return message["conversation"], "texto", None
    texto = (message.get("extendedTextMessage") or {}).get("text")
    if texto:
        return texto, "texto", None
    for campo, tipo in (
        ("imageMessage", "imagem"),
        ("videoMessage", "documento"),
        ("audioMessage", "audio"),
        ("documentMessage", "documento"),
        ("stickerMessage", "imagem"),
    ):
        bloco = message.get(campo) or {}
        if bloco:
            return bloco.get("caption") or "", tipo, bloco.get("url")
    return None, "texto", None


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
        conteudo, tipo, url_arquivo = _extrair_mensagem_bruta(message)
        result = {
            "whatsapp_number": remote_jid.removesuffix("@s.whatsapp.net"),
            "conteudo": conteudo,
            "tipo": tipo,
            "whatsapp_message_id": key.get("id"),
        }
        if url_arquivo:
            result["url_arquivo"] = url_arquivo
        if remetente:
            result["remetente"] = remetente
        return result

    return body


@router.post("/mensagem")
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
    duplicada = bool(mensagem.get("duplicada"))
    if not duplicada:
        await manager.send_event(
            mensagem["chat_id"], "nova_mensagem",
            {"chat_id": mensagem["chat_id"], "mensagem_id": mensagem["id"]},
        )
    code = status.HTTP_200_OK if duplicada else status.HTTP_201_CREATED
    return JSONResponse(status_code=code, content=mensagem)


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
