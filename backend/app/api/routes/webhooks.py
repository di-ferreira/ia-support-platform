import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.api.deps import get_repositories
from app.api.websocket_manager import manager
from app.appwrite.repositories import Repositories
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.models.enums import CanalAvaliacao
from app.models.mensagem import TipoMensagem
from app.schemas.webhook import (
    WebhookClienteUpdate,
    WebhookContexto,
    WebhookMensagem,
    WebhookSolucaoRequest,
    WebhookSolucaoResponse,
    WebhookStatusUpdate,
)
from app.services.ai_pipeline import AIPipelineService
from app.services.auditoria_service import Ator
from app.services.avaliacao_service import AvaliacaoService
from app.services.evolution_service import EvolutionService
from app.services.midia_service import MidiaService
from app.services.webhook_service import WebhookService

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks (n8n)"],
    dependencies=[Depends(rate_limit(120, 60))],
)

logger = logging.getLogger(__name__)


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
    """Deriva (conteudo, tipo, url_arquivo) do bloco `message` do payload bruto.

    O terceiro elemento é sempre `None`: a URL do CDN do WhatsApp expira e a
    mídia passa a chegar pelo campo `midia` (processada pela `MidiaService`).
    """
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
    ):
        bloco = message.get(campo) or {}
        if bloco:
            return bloco.get("caption") or "", tipo, None
    if message.get("stickerMessage"):
        return "", "sticker", None
    if message.get("locationMessage"):
        return "[localização]", "local", None
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
        conteudo, tipo, _ = _extrair_mensagem_bruta(message)
        result = {
            "whatsapp_number": remote_jid.removesuffix("@s.whatsapp.net"),
            "conteudo": conteudo,
            "tipo": tipo,
            "whatsapp_message_id": key.get("id"),
        }
        if tipo != "texto" and message:
            result["midia"] = {"key": key, "message": message}
        if remetente:
            result["remetente"] = remetente
        return result

    return body


TIPO_MENSAGEM_EVOLUTION = {
    "conversation": "texto",
    "extendedTextMessage": "texto",
    "imageMessage": "imagem",
    "videoMessage": "documento",
    "audioMessage": "audio",
    "documentMessage": "documento",
    "documentWithCaptionMessage": "documento",
    "stickerMessage": "sticker",
    "locationMessage": "local",
}
TIPOS_VALIDOS = tuple(e.value for e in TipoMensagem)


@router.post("/mensagem")
async def webhook_mensagem(
    request: Request,
    repos: Repositories = Depends(get_repositories),
    webhook_auth: None = Depends(verify_webhook),
):
    body = await request.json()
    payload = _normalizar_payload(body)
    tipo = payload.get("tipo")
    if tipo:
        payload["tipo"] = TIPO_MENSAGEM_EVOLUTION.get(tipo, tipo)
    if payload.get("tipo") not in TIPOS_VALIDOS + (None,):
        payload["tipo"] = "texto"
    validated = WebhookMensagem(**payload)
    data = validated.model_dump(exclude={"midia": True})
    if validated.midia is not None:
        data["url_arquivo"] = None
        try:
            resultado = await MidiaService().armazenar(
                validated.midia,
                validated.tipo.value,
                whatsapp_message_id=validated.whatsapp_message_id,
                conteudo=validated.conteudo,
            )
        except Exception as exc:
            logger.warning("Midia: falha ao processar no webhook: %s", exc)
            resultado = None
        if resultado:
            data["url_arquivo"], data["conteudo"] = resultado
    service = WebhookService(repos)
    mensagem = await service.receber_mensagem(data)
    duplicada = bool(mensagem.get("duplicada"))
    if not duplicada:
        await manager.send_event(
            mensagem["chat_id"], "nova_mensagem",
            {"chat_id": mensagem["chat_id"], "mensagem_id": mensagem["id"]},
        )
        if mensagem.get("remetente") == "cliente":
            await _capturar_avaliacao_csat(repos, mensagem)
    code = status.HTTP_200_OK if duplicada else status.HTTP_201_CREATED
    return JSONResponse(status_code=code, content=mensagem)


async def _capturar_avaliacao_csat(repos: Repositories, mensagem: dict) -> None:
    """Captura a nota CSAT respondida pelo cliente no webhook (best-effort).

    Toda falha é registrada como warning e nunca propaga: o salvamento da
    mensagem já aconteceu e a resposta continua a ser devolvida normalmente.
    Mensagens que não são nota (ex.: "quero falar com atendente") não consomem
    a pendência nem alteram a resposta.
    """
    logger = logging.getLogger(__name__)
    try:
        chat = await repos.chats.get(mensagem["chat_id"])
        if not chat or not chat.get("avaliacao_pendente"):
            return
        nota = AvaliacaoService.validar_nota(mensagem.get("conteudo"))
        if nota is None:
            return
        await AvaliacaoService(repos).registrar(
            mensagem["chat_id"],
            nota,
            canal=CanalAvaliacao.whatsapp,
        )
        await EvolutionService().enviar_texto(
            instance_name=settings.evolution_instance_name,
            number=chat["whatsapp_number"],
            text="Obrigado pela sua avaliação!",
        )
        mensagem["avaliacao_registrada"] = nota
    except Exception as exc:
        logger.warning("Falha ao capturar avaliação CSAT no webhook: %s", exc)


@router.patch("/chat/status")
async def webhook_status(
    body: WebhookStatusUpdate,
    repos: Repositories = Depends(get_repositories),
    webhook_auth: None = Depends(verify_webhook),
):
    service = WebhookService(repos)
    chat = await service.atualizar_status(body.chat_id, body.status, ator=Ator.servico("n8n"))
    await manager.send_event(
        body.chat_id, "status_update",
        {"chat_id": body.chat_id, "status": body.status.value},
    )
    return chat


# 03-18: o webhook de diagnóstico foi removido — o diagnóstico passou a ser
# gravado pelo backend em `ai_pipeline._finalizar` (gap 05-2); o webhook
# ficou sem chamador e duplicava a escrita.


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


@router.post("/n8n/erro")
async def webhook_n8n_erro(
    request: Request,
    webhook_auth: None = Depends(verify_webhook),
):
    """06-18: registro estruturado de falhas do workflow n8n.

    O nó "Registrar falha" do workflow aciona esta rota quando um nó HTTP
    falha após os retries. O payload varia por nó, então nada é validado:
    o resultado é sempre uma linha de log ``event=n8n_falha`` e um 202.
    """
    try:
        body = await request.json()
    except Exception:
        body = None
    if not isinstance(body, dict) or not body:
        logger.error(
            "event=n8n_falha workflow=%s node=%s chat_id=%s execution_id=%s erro=%s",
            None, None, None, None, "payload inválido",
        )
        return JSONResponse({"ok": True}, status_code=202)
    logger.error(
        "event=n8n_falha workflow=%s node=%s chat_id=%s execution_id=%s erro=%s",
        body.get("workflow"),
        body.get("node"),
        body.get("chat_id"),
        body.get("execution_id"),
        body.get("mensagem") or body.get("message"),
    )
    return JSONResponse({"ok": True}, status_code=202)
